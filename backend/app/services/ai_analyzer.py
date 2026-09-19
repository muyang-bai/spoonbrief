"""
AI 分析服务：二阶段流水线
Stage 1: 信息抽取
Stage 2: 全局分析师（含个性化）
"""

from __future__ import annotations
import json
import re
from pathlib import Path
from typing import Optional, Dict, List

from openai import AsyncOpenAI
from loguru import logger

from app.config import get_settings
from app.models.prompt_template import PromptTemplate
from app.models.api_key import ApiKey
from app.models.user import User
from app.utils.crypto import decrypt_value
from app.services.prompt_engine import get_default_prompt_template, render_prompt

settings = get_settings()

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"


def _load_prompt(filename: str) -> str:
    return (PROMPTS_DIR / filename).read_text(encoding="utf-8")


EXTRACTION_SYSTEM = "你是信息抽取引擎，只输出 JSON。"
EXTRACTION_USER_TEMPLATE = _load_prompt("extraction.txt")

# Combined analyst + personalization in one prompt
ANALYST_SYSTEM = _load_prompt("analyst.txt")


def _clean_ai_output(text: str) -> str:
    """Clean AI output: remove noise, preserve HTML content"""
    if not text or not text.strip():
        return ""

    # Remove thinking/reasoning blocks (DeepSeek R1)
    text = re.sub(r'<thinking>.*?</thinking>', '', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<reasoning>.*?</reasoning>', '', text, flags=re.DOTALL | re.IGNORECASE)

    # Remove markdown code fences
    text = re.sub(r'```[a-zA-Z]*\s*', '', text)
    text = text.replace('```', '')

    # Extract body if full HTML document
    body = re.search(r'<body[^>]*>(.*?)</body>', text, re.DOTALL | re.IGNORECASE)
    if body:
        text = body.group(1)

    # Remove DOCTYPE/html/head
    text = re.sub(r'<!DOCTYPE[^>]*>', '', text, flags=re.IGNORECASE)
    text = re.sub(r'</?html[^>]*>', '', text, flags=re.IGNORECASE)
    text = re.sub(r'<head>.*?</head>', '', text, flags=re.DOTALL | re.IGNORECASE)

    text = text.strip()

    # If still empty after cleaning
    if not text:
        return ""

    # Detect if output contains any HTML tags
    has_html = bool(re.search(r'<\s*(p|div|h[1-6]|ul|ol|li|table|span|br|strong|em|a|section|article|blockquote|b|i)(?:\s|>)', text, re.IGNORECASE))

    if not has_html:
        # Wrap plain text in proper HTML paragraphs
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        if not paragraphs:
            # Try splitting by single newlines
            lines = [l.strip() for l in text.split('\n') if l.strip()]
            paragraphs = lines
        text = '\n'.join(f'<p>{p}</p>' for p in paragraphs)

    return text


class AIAnalyzer:
    """AI 分析器：二阶段流水线"""

    async def analyze(
        self,
        news_items: List[Dict],
        user: User,
        db_session,
        subscription_prompt_id: Optional[int] = None,
        subscription_api_key_id: Optional[int] = None,
        keywords: Optional[List[str]] = None,
    ) -> str:
        # 1. Determine prompt template
        prompt_tpl = None
        if subscription_prompt_id:
            prompt_tpl = db_session.get(PromptTemplate, subscription_prompt_id)
        if not prompt_tpl:
            prompt_tpl = get_default_prompt_template(db_session)

        # 2. Get API client
        client, model = await self._get_client(user, db_session, prompt_tpl.model, subscription_api_key_id)

        if not client:
            logger.warning("AI analysis skipped: no available API")
            return "<p>AI analysis service unavailable.</p>"

        # 3. Stage 1: Information Extraction
        # 标题带编号：AI 引用「据[N]」与邮件中的条目编号一一对应
        numbered = [{**it, "title": f"[{i + 1}] {it.get('title', '')}"}
                    for i, it in enumerate(news_items[:12])]
        news_json = json.dumps(numbered, ensure_ascii=False)
        extraction_user = EXTRACTION_USER_TEMPLATE.replace("{news_json}", news_json)

        extraction_raw = await self._call_llm(
            client, model,
            system=EXTRACTION_SYSTEM,
            user=extraction_user,
            temperature=0.3,
            max_tokens=4000,
            retry_empty=False,  # 抽取失败直接用原始 JSON 兜底，不浪费重试预算
        )
        extraction = _clean_ai_output(extraction_raw)
        if not extraction:
            extraction = json.dumps(news_items[:20], ensure_ascii=False, indent=2)
        # 压缩喂给第二阶段的文本，降低推理型模型的思考负担
        if len(extraction) > 3200:
            extraction = extraction[:3200]
        logger.info(f"Stage 1 extraction done: {len(extraction)} chars")

        # 4. Parse user persona
        persona = {}
        if user.persona_json:
            try:
                persona = json.loads(user.persona_json)
            except json.JSONDecodeError:
                pass

        # 5. Stage 2: Global Analyst (combined with personalization)
        system_prompt, user_prompt = render_prompt(prompt_tpl, extraction, persona)

        # Augment system prompt with persona context
        if persona:
            persona_str = json.dumps(persona, ensure_ascii=False)
            system_prompt = system_prompt.replace("{persona}", persona_str)
        else:
            system_prompt = system_prompt.replace("{persona}", "未提供")

        # 注入订阅关键词：AI 必须围绕用户关注方向展开（此前分析跑题的直接原因）
        if keywords:
            kw_str = "、".join(keywords)
            user_prompt += (
                f"\n\n## 用户关注方向（订阅关键词）\n{kw_str}\n"
                "请务必围绕以上方向展开分析，优先回应与这些关键词直接相关的进展；"
                "若素材中没有相关新闻，请如实说明并给出最接近的相关信息。"
            )

        analysis_raw = await self._call_llm(
            client, model,
            system=system_prompt,
            user=user_prompt,
            temperature=prompt_tpl.temperature / 100,
            max_tokens=8000,  # 推理型模型需为思考留预算，否则 finish=length 内容为空
        )

        final_html = _clean_ai_output(analysis_raw)

        # 若模型仍输出了整页结构/样式垃圾（说明分析未完成），回退为新闻列表
        if final_html and ("<style" in final_html or "<head" in final_html):
            logger.warning("AI 输出包含整页样式结构，判定为无效分析，使用新闻列表兜底")
            final_html = ""

        # Fallback: if AI returned very little, show news items formatted
        if not final_html or len(final_html) < 100:
            logger.warning(f"AI returned short output ({len(final_html)} chars), using fallback")
            fallback = ['<h3>热点信息汇总</h3>']
            for item in news_items[:10]:
                title = item.get('title', '无标题')
                summary = item.get('summary', '')
                source = item.get('source', '未知来源')
                fallback.append(f'<p><strong>{title}</strong><br/>{summary}<br/><small>来源: {source}</small></p>')
            final_html = '\n'.join(fallback)

        logger.info(f"Stage 2 analysis done: {len(final_html)} chars")
        return final_html

    async def _get_client(self, user: User, db_session, preferred_model: str, api_key_id: Optional[int] = None):
        """Get API client: specified key > user key > platform key pool > platform config > .env fallback"""
        # 1. Subscription-specified api_key_id
        if api_key_id:
            key = db_session.get(ApiKey, api_key_id)
            if key and key.is_active:
                try:
                    decrypted = decrypt_value(key.encrypted_key)
                    base_url = key.base_url or settings.deepseek_base_url
                    model = key.model or preferred_model
                    client = AsyncOpenAI(api_key=decrypted, base_url=base_url)
                    logger.info(f"Using subscription API: provider={key.provider} model={model}")
                    return client, model
                except Exception as e:
                    logger.error(f"Subscription key decrypt failed: {e}")

        # 2. User's own key
        user_key = db_session.query(ApiKey).filter(
            ApiKey.user_id == user.id, ApiKey.is_active == True,
        ).first()
        if user_key:
            try:
                decrypted = decrypt_value(user_key.encrypted_key)
                base_url = user_key.base_url or settings.deepseek_base_url
                model = user_key.model or preferred_model
                client = AsyncOpenAI(api_key=decrypted, base_url=base_url)
                logger.info(f"Using user API: provider={user_key.provider}")
                return client, model
            except Exception as e:
                logger.error(f"User key decrypt failed: {e}")

        # 3. Platform config from database
        from app.models.system_config import SystemConfig
        db_cfgs = {c.key: c.value for c in db_session.query(SystemConfig).filter(
            SystemConfig.key.in_(["ai_provider", "ai_api_key", "ai_base_url", "ai_model", "ai_enabled"])
        ).all()}
        db_enabled = db_cfgs.get("ai_enabled", str(settings.ai_enabled)).lower() in ("true", "1", "yes")
        db_api_key = db_cfgs.get("ai_api_key") or settings.deepseek_api_key or settings.volcano_api_key
        db_base_url = db_cfgs.get("ai_base_url") or settings.deepseek_base_url
        db_model = db_cfgs.get("ai_model") or settings.deepseek_model or preferred_model

        if db_enabled and db_api_key:
            client = AsyncOpenAI(api_key=db_api_key, base_url=db_base_url)
            logger.info(f"Using platform default API: model={db_model}")
            return client, db_model

        return None, None

    async def _call_llm(self, client: AsyncOpenAI, model: str, system: str, user: str,
                        temperature: float = 0.7, max_tokens: int = 1500,
                        retry_empty: bool = True) -> str:
        """调用 LLM：空内容/异常自动重试一次（推理型模型偶发把额度花在思考上导致 content 为空）"""
        import asyncio
        attempts = (1, 2) if retry_empty else (1,)
        for attempt in attempts:
            try:
                resp = await client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                    temperature=temperature,
                    max_tokens=max_tokens,
                    timeout=120,
                )
                choice = resp.choices[0]
                finish = getattr(choice, "finish_reason", None)
                content = choice.message.content
                if content is None:
                    logger.error(f"LLM 返回 None content (attempt={attempt}, finish={finish})")
                    if attempt == 2:
                        return ""
                    await asyncio.sleep(3)
                    continue
                content = content.strip()
                if content:
                    if finish == "length":
                        logger.warning("LLM 输出达到 max_tokens 上限，内容可能被截断")
                    return content
                logger.warning(f"LLM 返回空内容 (attempt={attempt}, finish={finish})，3 秒后重试")
                if attempt == 2:
                    return ""
                await asyncio.sleep(3)
            except Exception as e:
                logger.error(f"LLM call failed (attempt={attempt}): {e}")
                if attempt == 2:
                    return ""
                await asyncio.sleep(3)
        return ""


_analyzer: Optional[AIAnalyzer] = None


def get_analyzer() -> AIAnalyzer:
    global _analyzer
    if _analyzer is None:
        _analyzer = AIAnalyzer()
    return _analyzer