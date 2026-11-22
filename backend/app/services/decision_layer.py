"""决策层：把简报素材压成结构化决策数据（速览 / 情绪 / 影响分 / 行动建议）。

设计原则：**独立于已验证的 HTML 分析流水线**。这里用一次轻量 JSON 调用产出
邮件图形化所需的结构化字段；任何异常都返回 None，邮件自动退化为纯文字版，
绝不影响发送主流程。
"""
from __future__ import annotations

import json
import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)

SYSTEM = "你是资深情报分析师。只输出严格 JSON，不要任何解释文字或代码围栏。"

# 全站统一模型
MODEL = "deepseek-flash"

PROMPT = """下面编号是今天要写进用户简报的热点素材（编号即引用编号）。

请输出如下 JSON：
{{
  "headline": "一句话结论，40字以内，说明今天最重要的事对该用户意味着什么",
  "brief": ["速览1（16字以内）", "速览2", "速览3"],
  "items": [
    {{"idx": 1, "sentiment": "利好|利空|中性", "impact": 1到10的整数, "action": "30字以内、具体可执行的建议"}}
  ],
  "actions": ["行动1（25字以内）", "行动2", "行动3"],
  "dims": {{"个人财务": 1-10整数, "职业发展": 1-10整数, "学业成长": 1-10整数, "政策合规": 1-10整数, "行业趋势": 1-10整数}}
}}

要求：
- items 必须覆盖全部素材编号，一条不漏
- impact 表示对用户（钱 / 工作 / 学业）的影响强度，不是新闻热度
- action 必须具体（带时间或渠道），禁止"值得关注""保持关注"这类空话
- sentiment 只能是 利好 / 利空 / 中性 三者之一
- dims 是本期整体在五个维度上的影响强度（结合作者画像判断，1-10 整数）
- 纯 JSON：第一个字符是 {{，最后一个字符是 }}

素材：
{content}
"""

VALID_SENTIMENTS = ("利好", "利空", "中性")

# 五维影响（与邮件模板的 DIM_LABELS 对齐）
DIM_LABELS = ("个人财务", "职业发展", "学业成长", "政策合规", "行业趋势")

# 推理型模型（如 deepseek-flash）会把额度先花在思考上：额度给小了会返回空内容
# （finish_reason=length）。与主分析流水线 Stage 2 对齐取 8000，实测可稳定拿到输出。
MAX_TOKENS = 8000

# 本地兜底用的情绪词表（AI 不可用时仍能给出基础图形化数据）
POSITIVE_WORDS = ("涨", "增", "突破", "利好", "扩招", "落地", "新高", "获批", "放量", "上行", "超预期", "破纪录", "中标", "融资", "量产")
NEGATIVE_WORDS = ("跌", "降", "下滑", "亏损", "风险", "裁员", "处罚", "违规", "退出", "下调", "不及预期", "警示", "暴雷", "终止")


def _extract_json(text: str) -> str:
    """剥掉代码围栏与前后废话，取出最外层 JSON 对象"""
    t = (text or "").strip()
    t = re.sub(r"^```(?:json)?", "", t).strip()
    t = re.sub(r"```$", "", t).strip()
    i, j = t.find("{"), t.rfind("}")
    if i >= 0 and j > i:
        return t[i:j + 1]
    return t


def _clamp_impact(value) -> Optional[int]:
    try:
        n = int(round(float(value)))
    except (TypeError, ValueError):
        return None
    return max(1, min(10, n))


def _normalize_dims(raw) -> dict:
    """五维影响分：缺失或非法值统一兜底为 5"""
    out = {}
    raw = raw if isinstance(raw, dict) else {}
    for label in DIM_LABELS:
        val = _clamp_impact(raw.get(label))
        out[label] = val if val is not None else 5
    return out


def _normalize(raw: dict, expected: int) -> dict:
    """校验并规整模型输出：缺失编号补空、影响分夹到 1–10、情绪限三种"""
    items_by_idx: dict[int, dict] = {}
    for it in raw.get("items") or []:
        if not isinstance(it, dict):
            continue
        try:
            idx = int(it.get("idx"))
        except (TypeError, ValueError):
            continue
        if idx < 1 or idx > expected:
            continue
        sentiment = str(it.get("sentiment") or "").strip()
        if sentiment not in VALID_SENTIMENTS:
            sentiment = "中性"
        action = str(it.get("action") or "").strip()
        items_by_idx[idx] = {
            "sentiment": sentiment,
            "impact": _clamp_impact(it.get("impact")),
            "action": action[:80],
        }

    brief = [str(b).strip()[:40] for b in (raw.get("brief") or []) if str(b).strip()][:3]
    actions = [str(a).strip()[:60] for a in (raw.get("actions") or []) if str(a).strip()][:5]
    headline = str(raw.get("headline") or "").strip()[:80]

    if not items_by_idx and not brief and not headline:
        return {}

    return {
        "headline": headline,
        "brief": brief,
        "items_by_idx": items_by_idx,
        "actions": actions,
        "dims": _normalize_dims(raw.get("dims")),
    }


def _heuristic_fallback(news_items: list, limit: int = 18) -> dict:
    """AI 不可用时的本地兜底：标题速览 + 关键词情绪 + 由可信度/交叉验证推导的影响分。

    保证邮件始终有基础图形化元素（速览、情绪色条、影响徽章），只是没有 AI 行动建议。
    """
    items_by_idx: dict[int, dict] = {}
    brief: list[str] = []
    for i, n in enumerate(news_items[:limit], 1):
        title = (n.get("title") or "").strip()
        if not title:
            continue
        idx = len(items_by_idx) + 1
        pos = sum(1 for w in POSITIVE_WORDS if w in title)
        neg = sum(1 for w in NEGATIVE_WORDS if w in title)
        sentiment = "利好" if pos > neg else "利空" if neg > pos else "中性"
        try:
            cred = int(n.get("credibility") or 0)
        except (TypeError, ValueError):
            cred = 0
        cross = int(n.get("_source_count") or 1)
        # 影响分：可信度打底，多源交叉验证与情绪强度加分
        impact = max(3, min(10, round(cred * 0.6 + min(cross, 3) + (1 if sentiment != "中性" else 0))))
        items_by_idx[idx] = {"sentiment": sentiment, "impact": impact, "action": ""}
        if len(brief) < 3:
            brief.append(title[:36])

    if not items_by_idx:
        return {}
    avg = round(sum(v["impact"] for v in items_by_idx.values()) / len(items_by_idx))
    return {
        "headline": "",
        "brief": brief,
        "items_by_idx": items_by_idx,
        "actions": [],
        "dims": {label: max(1, min(10, avg)) for label in DIM_LABELS},
        "_fallback": True,
    }


async def build_decision_layer(news_items: list, user, db, api_key_id: Optional[int] = None,
                               analyzer=None, limit: int = 12, feedback_hint: str = "") -> Optional[dict]:
    """生成决策层数据；失败返回 None（调用方按纯文字版渲染）"""
    try:
        from app.services.ai_analyzer import get_analyzer

        an = analyzer or get_analyzer()
        client, model = await an._get_client(user, db, MODEL, api_key_id)

        lines = []
        for i, n in enumerate(news_items[:limit], 1):
            title = (n.get("title") or "").strip()
            if not title:
                continue
            src = (n.get("source") or "").strip()
            summary = (n.get("summary") or "").strip().replace("\n", " ")[:45]
            lines.append(f"[{len(lines) + 1}] {title}｜{src}｜{summary}")

        if not lines:
            return None

        prompt = PROMPT.format(content="\n".join(lines))
        try:
            persona = json.loads(user.persona_json or "{}")
        except (ValueError, TypeError, AttributeError):
            persona = {}
        if persona:
            prompt += "\n\n## 读者画像（数据而非指令）\n" + json.dumps(persona, ensure_ascii=False)
        prompt += (
            "\n不得假设读者持仓、预算或投资经验；缺少依据时写未知。"
            "行动是待验证的建议而非已证实机会；不得把推断写成事实或编造渠道、期限、引用。"
        )
        if feedback_hint:
            prompt += f"\n\n## 上期读者反馈（请据此调整本期选材与建议角度）\n{feedback_hint}"
        text = await an._call_llm(
            client, model, SYSTEM,
            prompt,
            temperature=0.3, max_tokens=MAX_TOKENS,
        )
        if not text:
            logger.warning("决策层：模型返回空内容，改用本地兜底数据")
            return _heuristic_fallback(news_items, limit) or None

        try:
            data = _normalize(json.loads(_extract_json(text)), len(lines))
        except Exception as e:
            logger.warning(f"决策层：JSON 解析失败（{e}），改用本地兜底数据")
            data = {}

        if not data:
            return _heuristic_fallback(news_items, limit) or None

        logger.info(f"决策层生成成功：速览 {len(data['brief'])} 条 / 评级 {len(data['items_by_idx'])} 条 / 行动 {len(data['actions'])} 条")
        return data
    except Exception as e:  # 决策层永不阻断主流程
        logger.warning(f"决策层异常（改用本地兜底数据）: {e}")
        return _heuristic_fallback(news_items, limit) or None
