"""合规文本：备案号、隐私政策、退订说明（t110 · M2）

库里 compliance_texts 仍是「请填写…」占位时，用这里的兜底值，保证网站、邮件页脚始终显示真实备案号。
"""

from __future__ import annotations

ICP_RECORD = "蜀ICP备2026011042号-2"
ICP_URL = "https://beian.miit.gov.cn/"
PRIVACY_PATH = "/privacy"
UNSUBSCRIBE_HELP_PATH = "/unsubscribe-help"

DEFAULTS = {
    "icp_record": ICP_RECORD,
    "privacy_policy": "我们只收集提供简报所必需的信息：邮箱、画像与订阅设置、阅读反馈和用量记录。完整说明见网站「隐私政策」页。",
    "unsubscribe_notice": "不想再收到这份简报？点下方「退订」并确认，即可停止这份订阅；也可以登录控制台关闭订阅。",
    "disclaimer": "",
}


def is_placeholder(text: str | None) -> bool:
    t = (text or "").strip()
    return not t or t.startswith("请填写")


def effective(key: str, value: str | None) -> str:
    """库值有效就用库值，否则用兜底值。"""
    return DEFAULTS.get(key, "") if is_placeholder(value) else (value or "").strip()


def load(db) -> dict:
    from app.models.compliance_text import ComplianceText

    rows = {c.key: c.content for c in db.query(ComplianceText).all()}
    return {k: effective(k, rows.get(k)) for k in DEFAULTS}
