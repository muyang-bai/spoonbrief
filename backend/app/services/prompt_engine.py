"""
Prompt 引擎：从模板渲染最终提示词
"""

from __future__ import annotations
import json
from pathlib import Path
from typing import Dict, Tuple
from sqlalchemy.orm import Session
from loguru import logger

from app.models.prompt_template import PromptTemplate

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"


def _load_prompt(filename: str) -> str:
    return (PROMPTS_DIR / filename).read_text(encoding="utf-8")


BUILTIN_SYSTEM_PROMPT = _load_prompt("analyst.txt").split("## 读者画像")[0].strip()

BUILTIN_USER_TEMPLATE = """## 读者画像
{persona}

## 抽取的结构化信息
{content}

开始分析。"""


def get_default_prompt_template(db: Session) -> PromptTemplate:
    """获取或创建默认Prompt模板"""
    tpl = db.query(PromptTemplate).filter(
        PromptTemplate.is_default == True,
        PromptTemplate.is_active == True,
    ).first()

    if not tpl:
        tpl = PromptTemplate(
            name="全局分析师-默认",
            system_prompt=BUILTIN_SYSTEM_PROMPT,
            user_prompt_template=BUILTIN_USER_TEMPLATE,
            model="deepseek-v4-flash",
            temperature=70,
            max_tokens=1500,
            is_default=True,
            is_active=True,
        )
        db.add(tpl)
        db.commit()
        db.refresh(tpl)

    return tpl


def render_prompt(template: PromptTemplate, content: str, persona: Dict) -> Tuple[str, str]:
    """
    Render system and user prompts from template.
    ALWAYS ensures content and persona are included, even if template
    doesn't have explicit placeholders.
    """
    system = template.system_prompt or ""

    user = template.user_prompt_template or ""

    # Replace placeholders if they exist
    persona_str = json.dumps(persona, ensure_ascii=False) if persona else "未提供"

    has_content_placeholder = "{content}" in user
    has_persona_placeholder = "{persona}" in user

    if has_content_placeholder:
        user = user.replace("{content}", content)
    if has_persona_placeholder:
        user = user.replace("{persona}", persona_str)

    # CRITICAL: If template lacks placeholders, APPEND content at the end
    # so the AI actually receives the news data to analyze
    if not has_content_placeholder:
        logger.warning(f"Template '{template.name}' missing {{content}} placeholder, appending content")
        user += f"\n\n## 待分析的热点信息\n{content}"

    if not has_persona_placeholder and persona:
        user += f"\n\n## 读者画像\n{persona_str}"

    return system, user