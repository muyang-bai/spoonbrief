"""用户画像：结构化字段 → 可读画像文本 / 完成度评分 / 隐式行为观察

设计参考：
- LaMP（ACL 2024《When Large Language Models Meet Personalization》）：
  个性化 = 显式用户档案 + 历史行为检索，两者都要喂给模型
- HYDRA（NeurIPS 2024）：把「用户偏好建模」与「通用能力」分开，偏好单独成层
- IAB Tech Lab Content Taxonomy 2.2 / Data Transparency Standard：
  用标准化兴趣分类替代纯自由文本，并向用户透明展示「AI 到底看到了什么」
- Microsoft MIND / NPA 新闻推荐：用户侧用兴趣分布 + 行为反馈建模（本模块的隐式观察）
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta

# 关注方向分类（对齐产品 14 个信源的覆盖范围）
DOMAIN_OPTIONS = [
    "AI 与大模型", "算力与芯片", "半导体产业链", "新能源与储能", "智能汽车",
    "低空经济", "人形机器人", "生物医药", "消费与出海", "宏观与黄金",
    "教育政策", "房地产与城市", "数字经济与就业", "开源与技术社区",
]

GOAL_OPTIONS = [
    "升学考研", "求职跳槽", "副业变现", "投资决策", "创业选赛道",
    "行业洞察", "教学备课", "内容选题", "企业情报监测",
]

CONTENT_PREF_OPTIONS = [
    "政策与文件", "技术进展", "资本动向", "产品发布", "学术研究", "数据与报告",
]

OUTPUT_OPTIONS = [
    "行动清单", "机会与风险", "交叉视角", "可引用数据", "选题灵感", "竞品动态",
]

AVOID_OPTIONS = [
    "娱乐八卦", "体育赛事", "国际政治", "加密货币", "明星绯闻", "广告营销轰炸",
]

IDENTITY_OPTIONS = [
    "学生", "求职者", "职场人", "创业者", "投资者",
    "创作者", "研究者", "教师", "公务员", "自由职业",
]

PERSPECTIVE_OPTIONS = ["个人决策", "团队决策", "机构/企业决策"]
HORIZON_OPTIONS = ["当天就要用", "1-3 个月内", "半年以上"]
RISK_OPTIONS = ["保守型", "平衡型", "激进型"]
LENGTH_OPTIONS = ["30 秒速览就够", "3 分钟读完", "愿意读深度长文"]
TONE_OPTIONS = ["犀利直给", "中性客观", "通俗科普"]

SECTIONS = ("identities", "goals", "domains", "content_prefs", "outputs", "avoid")
TEXT_FIELDS = ("field", "role_title", "self_description", "pain_point", "extra_notes")


def _as_list(value) -> list:
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    if isinstance(value, str) and value.strip():
        return [s.strip() for s in value.replace("，", ",").split(",") if s.strip()]
    return []


def compose_persona_text(persona: dict) -> str:
    """把结构化画像拼成一段可读文本（给 AI 看的「人话版」，也是给用户看的透明化预览）"""
    if not persona:
        return ""
    p = persona or {}
    parts = []

    identities = _as_list(p.get("identities"))
    if identities:
        parts.append("我的身份：" + "、".join(identities))

    basics = []
    if p.get("field"):
        basics.append(f"所在领域/专业：{p['field']}")
    if p.get("role_title"):
        basics.append(f"角色/职级：{p['role_title']}")
    stu = p.get("student") or {}
    if isinstance(stu, dict):
        if stu.get("major"):
            basics.append(f"专业：{stu['major']}")
        if stu.get("target_school"):
            basics.append(f"目标院校：{stu['target_school']}")
    ent = p.get("entrepreneur") or {}
    if isinstance(ent, dict) and ent.get("stage"):
        basics.append(f"创业阶段：{ent['stage']}")
    if basics:
        parts.append("；".join(basics))

    goals = _as_list(p.get("goals"))
    if goals:
        parts.append("我最想解决的问题：" + "、".join(goals))

    domains = _as_list(p.get("domains")) or _as_list(p.get("interests"))
    if domains:
        parts.append("我长期关注的赛道：" + "、".join(domains))

    prefs = _as_list(p.get("content_prefs"))
    if prefs:
        parts.append("我偏好的内容类型：" + "、".join(prefs))

    avoid = _as_list(p.get("avoid"))
    if avoid:
        parts.append("我不想看的内容：" + "、".join(avoid))

    if p.get("perspective"):
        parts.append(f"我的决策视角：{p['perspective']}")
    if p.get("horizon"):
        parts.append(f"我关心的时间尺度：{p['horizon']}")
    if p.get("risk"):
        parts.append(f"风险偏好：{p['risk']}")
    if p.get("reading_length"):
        parts.append(f"阅读习惯：{p['reading_length']}")
    if p.get("tone"):
        parts.append(f"期望语气：{p['tone']}")

    outputs = _as_list(p.get("outputs"))
    if outputs:
        parts.append("我希望简报给出的东西：" + "、".join(outputs))

    if p.get("pain_point"):
        parts.append(f"我最近在纠结的事：{p['pain_point']}")
    if p.get("self_description"):
        parts.append(f"补充自我介绍：{p['self_description']}")
    if p.get("extra_notes"):
        parts.append(f"其他想让 AI 知道的：{p['extra_notes']}")

    return "。".join(parts) + "。" if parts else ""


def completeness(persona: dict) -> dict:
    """画像完成度：按维度加权，给出还缺什么（引导用户补齐）"""
    p = persona or {}
    checks = [
        ("身份角色", bool(_as_list(p.get("identities"))), 15, "选择你的身份，AI 会按身份交叉分析"),
        ("所在领域/专业", bool(p.get("field") or (p.get("student") or {}).get("major")), 12, "填上领域，赛道判断更准"),
        ("关注方向", len(_as_list(p.get("domains")) or _as_list(p.get("interests"))) >= 2, 18, "至少选 2 个方向，选材才有抓手"),
        ("想解决的问题", bool(_as_list(p.get("goals"))), 15, "选目标，建议才会落到行动上"),
        ("内容偏好", bool(_as_list(p.get("content_prefs"))), 10, "告诉我们你爱看哪类内容"),
        ("输出偏好", bool(_as_list(p.get("outputs"))), 10, "决定简报给你什么（行动清单？数据？）"),
        ("规避内容", bool(_as_list(p.get("avoid"))), 5, "不想看什么，同样重要"),
        ("阅读习惯", bool(p.get("reading_length")), 5, "决定简报篇幅"),
        ("一句话处境", bool(p.get("self_description") or p.get("pain_point")), 10, "写下最近的困扰，AI 才能对症"),
    ]
    score = sum(w for _n, ok, w, _h in checks if ok)
    missing = [{"label": n, "hint": h, "weight": w} for n, ok, w, h in checks if not ok]
    return {"score": score, "missing": missing}


def implicit_observations(db, user_id: int, days: int = 30) -> dict:
    """隐式观察（行为侧）：读后反馈、订阅方向、来源分布 —— 用户不用填，系统自己看"""
    out = {"feedback": {"up": 0, "down": 0, "useful_rate": None},
           "directions": [], "top_sources": [], "reports": 0}
    try:
        from sqlalchemy import func
        from app.models.report import Report
        from app.models.report_feedback import ReportFeedback
        from app.models.subscription import Subscription

        since = datetime.utcnow() - timedelta(days=days)
        rows = (
            db.query(ReportFeedback.value, func.count(ReportFeedback.id))
            .filter(ReportFeedback.user_id == user_id, ReportFeedback.created_at >= since)
            .group_by(ReportFeedback.value)
            .all()
        )
        fb = {r[0]: int(r[1]) for r in rows}
        up, down = fb.get("up", 0), fb.get("down", 0)
        out["feedback"] = {
            "up": up, "down": down,
            "useful_rate": round(up / (up + down) * 100, 1) if (up + down) else None,
        }

        subs = db.query(Subscription).filter(Subscription.user_id == user_id).all()
        for s in subs:
            kw = _as_list(getattr(s, "keywords", "") or "")
            if kw:
                out["directions"].append({"name": getattr(s, "name", "") or "未命名订阅", "keywords": kw[:8]})

        reports = (
            db.query(Report)
            .filter(Report.user_id == user_id, Report.created_at >= since)
            .order_by(Report.id.desc())
            .limit(30)
            .all()
        )
        out["reports"] = len(reports)
        src_count: dict[str, int] = {}
        for r in reports:
            try:
                items = json.loads(r.raw_news_json or "[]")
            except Exception:
                continue
            for it in items:
                src = (it.get("source") or "").strip()
                if src:
                    src_count[src] = src_count.get(src, 0) + 1
        out["top_sources"] = [
            {"name": k, "count": v}
            for k, v in sorted(src_count.items(), key=lambda kv: -kv[1])[:5]
        ]
    except Exception:
        pass
    return out
