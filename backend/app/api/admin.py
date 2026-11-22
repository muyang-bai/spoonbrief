"""Admin routes"""
from datetime import datetime, timedelta
from typing import List
import json
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import func, desc
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from app.database import get_db
from app.utils import secrets as secrets_util
from app.deps import get_admin_user
from app.models.user import User, UserRole
from app.models.ailifeos_link import AilifeosLink
from app.models.token_usage import TokenUsage
from app.models.subscription import Subscription
from app.models.report import Report
from app.models.news_source import NewsSource
from app.models.announcement import Announcement
from app.models.prompt_template import PromptTemplate
from app.models.keyword_stat import KeywordStat
from app.models.system_config import SystemConfig
from app.models.compliance_text import ComplianceText
from app.schemas.admin import (
    AnnouncementOut, AdminUserOut, AdminUserUpdate,
    SmtpConfig, AiConfig,
    DashboardStats,
    ComplianceTextUpdate, ComplianceTextOut,
    PromptTemplateCreate, PromptTemplateOut,
)

router = APIRouter(prefix="/admin", tags=["admin"])

@router.get("/dashboard", response_model=DashboardStats)
async def dashboard(admin: User = Depends(get_admin_user), db: Session = Depends(get_db)):
    total_users = db.query(func.count(User.id)).scalar() or 0
    active_users = db.query(func.count(User.id)).filter(User.is_active == True).scalar() or 0
    total_subs = db.query(func.count(Subscription.id)).scalar() or 0
    total_reports = db.query(func.count(Report.id)).scalar() or 0
    sent_reports = db.query(func.count(Report.id)).filter(Report.status == "sent").scalar() or 0

    top_keywords = db.query(KeywordStat.keyword, KeywordStat.search_count).order_by(desc(KeywordStat.search_count)).limit(20).all()
    keyword_top20 = [{"keyword": k, "count": c} for k, c in top_keywords]

    cat_dist = db.query(Subscription.category_id, func.count(Subscription.id)).group_by(Subscription.category_id).all()
    category_distribution = [{"name": c or "未分类", "count": cnt} for c, cnt in cat_dist]

    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    if db.bind.dialect.name == "sqlite":
        growth = db.query(
            func.date(User.created_at).label("date"),
            func.count(User.id).label("count"),
        ).filter(User.created_at >= thirty_days_ago).group_by("date").order_by("date").all()
    else:
        growth = db.query(
            func.date(User.created_at).label("date"),
            func.count(User.id).label("count"),
        ).filter(User.created_at >= thirty_days_ago).group_by("date").order_by("date").all()
    user_growth = [{"date": str(d), "count": c} for d, c in growth]

    now = datetime.utcnow()
    today_reports = db.query(func.count(Report.id)).filter(Report.created_at >= now.replace(hour=0,minute=0,second=0,microsecond=0)).scalar() or 0
    active_subs = db.query(func.count(Subscription.id)).filter(Subscription.is_active == True).scalar() or 0
    delivery_rate = round(sent_reports / total_reports * 100, 2) if total_reports > 0 else 0.0
    since = now - timedelta(hours=24)
    linked_users = db.query(func.count(AilifeosLink.user_id)).scalar() or 0
    reports_24h = db.query(func.count(Report.id)).filter(Report.created_at >= since).scalar() or 0
    failed_24h = db.query(func.count(Report.id)).filter(Report.created_at >= since, Report.status == "failed").scalar() or 0
    tokens_24h = db.query(func.coalesce(func.sum(TokenUsage.total_tokens), 0)).filter(TokenUsage.created_at >= since).scalar() or 0
    cost_24h = db.query(func.coalesce(func.sum(TokenUsage.cost_yuan), 0)).filter(TokenUsage.created_at >= since).scalar() or 0
    top_model = (
        db.query(TokenUsage.model, func.sum(TokenUsage.total_tokens))
        .filter(TokenUsage.created_at >= since, TokenUsage.model.isnot(None))
        .group_by(TokenUsage.model)
        .order_by(func.sum(TokenUsage.total_tokens).desc())
        .first()
    )
    topic_rows = db.query(Subscription.name, func.count(Subscription.id)).group_by(Subscription.name).order_by(func.count(Subscription.id).desc()).limit(20).all()
    subscription_topics = [{"name": n or "未命名", "count": int(c or 0)} for n, c in topic_rows]

    return DashboardStats(
        total_users=total_users,
        active_users=active_users,
        total_subscriptions=total_subs,
        total_reports_sent=sent_reports,
        total_emails_sent=sent_reports,
        keyword_top20=keyword_top20,
        category_distribution=category_distribution,
        user_growth=user_growth,
        email_delivery_rate=delivery_rate,
        total_reports=total_reports,
        today_reports=today_reports,
        active_subscriptions=active_subs,
        linked_users=int(linked_users),
        reports_24h=int(reports_24h),
        failed_24h=int(failed_24h),
        tokens_24h=int(tokens_24h or 0),
        cost_yuan_24h=round(float(cost_24h or 0), 4),
        token_model_24h=(top_model[0] if top_model and top_model[0] else None),
        subscription_topics=subscription_topics,
    )

@router.get("/users", response_model=List[AdminUserOut])
async def list_users(admin: User = Depends(get_admin_user), db: Session = Depends(get_db), page: int = Query(1, ge=1), size: int = Query(20, ge=1, le=100), keyword: str = Query("", description="搜索关键词")):
    offset = (page - 1) * size
    q = db.query(User)
    if keyword:
        q = q.filter(User.email.ilike(f"%{keyword}%") | User.nickname.ilike(f"%{keyword}%"))
    users = q.order_by(User.created_at.desc()).offset(offset).limit(size).all()
    result = []
    for u in users:
        sub_count = db.query(func.count(Subscription.id)).filter(Subscription.user_id == u.id).scalar() or 0
        raw = u.role.value if hasattr(u.role, 'value') else str(u.role or '')
        permission = 'admin' if str(raw).upper() == 'ADMIN' or str(raw).lower() == 'admin' else 'member'
        link = db.query(AilifeosLink).filter(AilifeosLink.user_id == u.id).first()
        stored = (link.tier if link else None) or None
        labels = {'FREE':'未开通','TRIAL':'体验用户','VIP':'VIP','SVIP':'SVIP','SSVIP':'SSVIP','SSSVIP':'SSSVIP'}
        tier_label = labels.get(str(stored).upper(), '未同步') if stored else '未同步'
        result.append(AdminUserOut(
            id=u.id, email=u.email, nickname=u.nickname, role=raw,
            is_active=u.is_active, created_at=u.created_at, last_login_at=u.last_login_at,
            subscription_count=sub_count,
            api_quota_total=u.api_quota_total,
            api_quota_used=u.api_quota_used,
            api_quota_reset_at=u.api_quota_reset_at,
            permission=permission,
            member_tier=stored,
            member_tier_label=tier_label,
        ))
    return result

@router.put("/users/{user_id}")
async def update_user(user_id: int, req: AdminUserUpdate, admin: User = Depends(get_admin_user), db: Session = Depends(get_db)):
    user = db.query(User).get(user_id)
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    if req.nickname:
        user.nickname = req.nickname
    if req.role:
        user.role = UserRole(req.role)
    if req.is_active is not None:
        user.is_active = req.is_active
    db.commit()
    return {"message": "User updated"}

@router.delete("/users/{user_id}")
async def delete_user(user_id: int, admin: User = Depends(get_admin_user), db: Session = Depends(get_db)):
    user = db.query(User).get(user_id)
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    db.delete(user)
    db.commit()
    return {"message": "User deleted"}


@router.get("/smtp")
async def get_smtp_config(admin: User = Depends(get_admin_user), db: Session = Depends(get_db)):
    cfg = db.query(SystemConfig).filter(SystemConfig.key.like("smtp_%")).all()
    return {c.key.replace("smtp_", ""): c.value for c in cfg}


@router.post("/smtp/test")
async def test_smtp(admin: User = Depends(get_admin_user), db: Session = Depends(get_db)):
    """测试SMTP连接：发送一封测试邮件到管理员邮箱"""
    cfg = {c.key.replace("smtp_", ""): c.value for c in db.query(SystemConfig).filter(SystemConfig.key.like("smtp_%")).all()}
    host = cfg.get("host", "")
    if not host:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "请先保存SMTP配置后再测试连接")

    try:
        from app.services.email_sender import send_email
        success = await send_email(
            [admin.email],
            "一勺热点 - SMTP测试邮件",
            "<h3>SMTP连接测试成功！</h3><p>如果你收到这封邮件，说明SMTP配置正确。</p>",
            from_email=cfg.get("from_email"),
            from_name=cfg.get("from_name"),
        )
        if success:
            return {"status": "ok", "message": f"测试邮件已发送至 {admin.email}，请检查收件箱"}
        else:
            raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "SMTP连接失败，请检查配置")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, f"SMTP测试失败：{str(e)}")

@router.put("/smtp")
async def update_smtp_config(req: SmtpConfig, admin: User = Depends(get_admin_user), db: Session = Depends(get_db)):
    for k, v in req.model_dump().items():
        if k == "password":
            v = secrets_util.seal(v)
        cfg = db.query(SystemConfig).filter(SystemConfig.key == f"smtp_{k}").first()
        if cfg:
            cfg.value = str(v) if v is not None else ""
        else:
            db.add(SystemConfig(key=f"smtp_{k}", value=str(v) if v is not None else ""))
    db.commit()
    return {"message": "SMTP config updated"}

@router.get("/ai-config")
async def get_ai_config(admin: User = Depends(get_admin_user), db: Session = Depends(get_db)):
    cfg = db.query(SystemConfig).filter(SystemConfig.key.like("ai_%")).all()
    return {c.key.replace("ai_", ""): c.value for c in cfg}

@router.put("/ai-config")
async def update_ai_config(req: AiConfig, admin: User = Depends(get_admin_user), db: Session = Depends(get_db)):
    for k, v in req.model_dump().items():
        if k == "api_key":
            v = secrets_util.seal(v)
        cfg = db.query(SystemConfig).filter(SystemConfig.key == f"ai_{k}").first()
        if cfg:
            cfg.value = str(v) if v is not None else ""
        else:
            db.add(SystemConfig(key=f"ai_{k}", value=str(v) if v is not None else ""))
    db.commit()
    return {"message": "AI config updated"}


@router.post("/ai-config/test")
async def test_ai_config(admin: User = Depends(get_admin_user), db: Session = Depends(get_db)):
    """测试AI接口连接"""
    cfg = {c.key.replace("ai_", ""): c.value for c in db.query(SystemConfig).filter(SystemConfig.key.like("ai_%")).all()}
    api_key = secrets_util.unseal(cfg.get("api_key", ""))
    if not api_key:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "请先保存AI配置后再测试连接")
    try:
        from openai import AsyncOpenAI
        base_url = cfg.get("base_url", "https://api.deepseek.com")
        model = cfg.get("model", "deepseek-v4-flash")
        client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        resp = await client.chat.completions.create(model=model, messages=[{"role":"user","content":"OK"}], max_tokens=256)
        content = (resp.choices[0].message.content or "").strip()
        return {"status": "ok", "message": "接口请求成功；" + (f"模型回复：{content[:120]}" if content else "模型未返回正文，不能视为内容质量验证通过") }
    except Exception as e:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, f"接口连接失败（{type(e).__name__}），请核对配置和服务商状态")


@router.get("/sources")
async def list_sources(admin: User = Depends(get_admin_user), db: Session = Depends(get_db)):
    return db.query(NewsSource).order_by(NewsSource.created_at.desc()).all()


# ═══ 合规文本 ═══

@router.get("/compliance", response_model=List[ComplianceTextOut])
async def list_compliance(admin: User = Depends(get_admin_user), db: Session = Depends(get_db)):
    return db.query(ComplianceText).all()


@router.put("/compliance")
async def update_compliance(req: ComplianceTextUpdate, admin: User = Depends(get_admin_user), db: Session = Depends(get_db)):
    row = db.query(ComplianceText).filter(ComplianceText.key == req.key).first()
    if row:
        row.content = req.content
        row.updated_at = datetime.utcnow()
    else:
        titles = {"icp_record": "备案号", "privacy_policy": "隐私政策", "unsubscribe_notice": "退订说明"}
        row = ComplianceText(key=req.key, title=titles.get(req.key, req.key), content=req.content)
        db.add(row)
    db.commit()
    return {"message": "已保存"}


# ═══ Prompt 模板 ═══

@router.get("/prompts", response_model=List[PromptTemplateOut])
async def list_prompts(admin: User = Depends(get_admin_user), db: Session = Depends(get_db)):
    return db.query(PromptTemplate).order_by(PromptTemplate.created_at.desc()).all()


@router.post("/prompts", response_model=PromptTemplateOut)
async def create_prompt(req: PromptTemplateCreate, admin: User = Depends(get_admin_user), db: Session = Depends(get_db)):
    if req.is_default:
        db.query(PromptTemplate).filter(PromptTemplate.is_default == True).update({"is_default": False})
    data = req.model_dump()
    data["is_platform"] = True
    data["owner_id"] = None
    tpl = PromptTemplate(**data)
    db.add(tpl)
    db.commit()
    db.refresh(tpl)
    return tpl


@router.put("/prompts/{tpl_id}", response_model=PromptTemplateOut)
async def update_prompt(tpl_id: int, req: PromptTemplateCreate, admin: User = Depends(get_admin_user), db: Session = Depends(get_db)):
    tpl = db.get(PromptTemplate, tpl_id)
    if not tpl:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "模板不存在")
    if req.is_default:
        db.query(PromptTemplate).filter(PromptTemplate.is_default == True, PromptTemplate.id != tpl_id).update({"is_default": False})
    for k, v in req.model_dump().items():
        if k in ("is_platform", "owner_id"):
            continue
        setattr(tpl, k, v)
    db.commit()
    db.refresh(tpl)
    return tpl


@router.delete("/prompts/{tpl_id}")
async def delete_prompt(tpl_id: int, admin: User = Depends(get_admin_user), db: Session = Depends(get_db)):
    tpl = db.get(PromptTemplate, tpl_id)
    if not tpl:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "模板不存在")
    db.delete(tpl)
    db.commit()
    return {"message": "已删除"}


# ═══ 公告管理（管理员列表） ═══

@router.get("/announcements", response_model=List[AnnouncementOut])
async def admin_list_announcements(admin: User = Depends(get_admin_user), db: Session = Depends(get_db)):
    return db.query(Announcement).order_by(Announcement.created_at.desc()).all()



# ━━━ 注册开关 ━━━

@router.get("/register-toggle")
async def get_register_toggle(admin: User = Depends(get_admin_user), db: Session = Depends(get_db)):
    cfg = db.query(SystemConfig).filter(SystemConfig.key == "allow_registration").first()
    return {"allow_registration": cfg.value if cfg else "true"}

class RegisterToggleRequest(BaseModel):
    allow_registration: bool

@router.post("/register-toggle")
async def set_register_toggle(req: RegisterToggleRequest, admin: User = Depends(get_admin_user), db: Session = Depends(get_db)):
    cfg = db.query(SystemConfig).filter(SystemConfig.key == "allow_registration").first()
    if cfg:
        cfg.value = "true" if req.allow_registration else "false"
    else:
        db.add(SystemConfig(key="allow_registration", value="true" if req.allow_registration else "false", description="是否允许新用户注册"))
    db.commit()
    return {"allow_registration": req.allow_registration}


# ━━━ API 配额管理 ━━━

@router.get("/users/{user_id}/quota")
async def get_user_quota(user_id: int, admin: User = Depends(get_admin_user), db: Session = Depends(get_db)):
    user = db.query(User).get(user_id)
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    return {
        "user_id": user.id,
        "api_quota_total": user.api_quota_total,
        "api_quota_used": user.api_quota_used,
        "api_quota_reset_at": user.api_quota_reset_at.isoformat() if user.api_quota_reset_at else None,
    }

class QuotaUpdateRequest(BaseModel):
    api_quota_total: int = Field(ge=0, description="月度API调用配额上限")
    api_quota_used: int = Field(default=0, ge=0)

@router.put("/users/{user_id}/quota")
async def update_user_quota(user_id: int, req: QuotaUpdateRequest, admin: User = Depends(get_admin_user), db: Session = Depends(get_db)):
    user = db.query(User).get(user_id)
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    user.api_quota_total = req.api_quota_total
    user.api_quota_used = req.api_quota_used
    db.commit()
    return {"message": "Quota updated", "user_id": user.id, "api_quota_total": user.api_quota_total, "api_quota_used": user.api_quota_used}

# ════════════════════════════════════════════════════════════════
# AI 用量看板：token 总量 / 预计费用 / 消耗最多用户 / 反馈闭环统计
# ════════════════════════════════════════════════════════════════
@router.get("/token-stats")
async def token_stats(
    days: int = Query(30, ge=1, le=180),
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    from datetime import datetime as _dt, timedelta as _td
    from app.models.token_usage import TokenUsage
    from app.models.report_feedback import ReportFeedback
    from app.services.usage_tracker import get_prices

    since = _dt.utcnow() - _td(days=days)
    price_in, price_out = get_prices(db)

    total_tokens, total_cost, calls = (
        db.query(
            func.coalesce(func.sum(TokenUsage.total_tokens), 0),
            func.coalesce(func.sum(TokenUsage.cost_yuan), 0.0),
            func.count(TokenUsage.id),
        )
        .filter(TokenUsage.created_at >= since)
        .first()
    )

    # 每日趋势
    daily_rows = (
        db.query(
            func.date(TokenUsage.created_at).label("d"),
            func.sum(TokenUsage.total_tokens),
            func.sum(TokenUsage.cost_yuan),
            func.count(TokenUsage.id),
        )
        .filter(TokenUsage.created_at >= since)
        .group_by(func.date(TokenUsage.created_at))
        .order_by(func.date(TokenUsage.created_at))
        .all()
    )
    daily = [
        {"date": str(r[0]), "tokens": int(r[1] or 0), "cost": round(float(r[2] or 0), 4), "calls": int(r[3] or 0)}
        for r in daily_rows
    ]

    # 消耗最多的前三用户
    top_rows = (
        db.query(
            TokenUsage.user_id,
            func.sum(TokenUsage.total_tokens).label("t"),
            func.sum(TokenUsage.cost_yuan).label("c"),
            func.count(TokenUsage.id).label("n"),
        )
        .filter(TokenUsage.created_at >= since, TokenUsage.user_id.isnot(None))
        .group_by(TokenUsage.user_id)
        .order_by(func.sum(TokenUsage.total_tokens).desc())
        .limit(3)
        .all()
    )
    top_users = []
    for r in top_rows:
        u = db.query(User).get(r[0])
        top_users.append({
            "user_id": r[0],
            "email": getattr(u, "email", "") if u else "",
            "tokens": int(r[1] or 0),
            "cost": round(float(r[2] or 0), 4),
            "calls": int(r[3] or 0),
        })

    # 按阶段拆分（分析 / 决策层）
    stage_rows = (
        db.query(TokenUsage.stage, func.sum(TokenUsage.total_tokens))
        .filter(TokenUsage.created_at >= since)
        .group_by(TokenUsage.stage)
        .all()
    )
    by_stage = [{"stage": r[0] or "analyze", "tokens": int(r[1] or 0)} for r in stage_rows]

    # 反馈闭环：有用 / 没用（验证「反馈有没有用」）
    fb_rows = (
        db.query(ReportFeedback.value, func.count(ReportFeedback.id))
        .filter(ReportFeedback.created_at >= since)
        .group_by(ReportFeedback.value)
        .all()
    )
    fb = {r[0]: int(r[1]) for r in fb_rows}
    up, down = fb.get("up", 0), fb.get("down", 0)
    feedback = {
        "up": up,
        "down": down,
        "total": up + down,
        "useful_rate": round(up / (up + down) * 100, 1) if (up + down) else None,
    }

    # 简报产出与平均单份成本
    from app.models.report import Report
    sent_count = (
        db.query(func.count(Report.id))
        .filter(Report.created_at >= since, Report.status == "sent")
        .scalar()
        or 0
    )

    # 全站累计（不受时间筛选影响）
    all_tokens, all_cost, all_calls = (
        db.query(
            func.coalesce(func.sum(TokenUsage.total_tokens), 0),
            func.coalesce(func.sum(TokenUsage.cost_yuan), 0.0),
            func.count(TokenUsage.id),
        ).first()
    )
    all_time = {"tokens": int(all_tokens or 0), "cost": round(float(all_cost or 0), 4), "calls": int(all_calls or 0)}

    # 模型分布
    model_rows = (
        db.query(TokenUsage.model,
                 func.sum(TokenUsage.total_tokens),
                 func.sum(TokenUsage.cost_yuan),
                 func.count(TokenUsage.id))
        .filter(TokenUsage.created_at >= since)
        .group_by(TokenUsage.model)
        .order_by(func.sum(TokenUsage.total_tokens).desc())
        .all()
    )
    by_model = [{"model": r[0] or "unknown", "tokens": int(r[1] or 0),
                 "cost": round(float(r[2] or 0), 4), "calls": int(r[3] or 0)} for r in model_rows]

    return {
        "days": days,
        "price": {"input": price_in, "output": price_out, "unit": "元/百万token"},
        "total_tokens": int(total_tokens or 0),
        "total_cost": round(float(total_cost or 0), 4),
        "calls": int(calls or 0),
        "sent_reports": int(sent_count),
        "avg_cost_per_report": round(float(total_cost or 0) / sent_count, 4) if sent_count else None,
        "daily": daily,
        "top_users": top_users,
        "by_stage": by_stage,
        "feedback": feedback,
        "all_time": all_time,
        "by_model": by_model,
    }

@router.get("/metrics/novelty")
async def novelty_metrics(days: int = Query(30, ge=1, le=180),
                          admin: User = Depends(get_admin_user),
                          db: Session = Depends(get_db)):
    """内容质量指标：去重效率 / 进展率 / 零新增次数（数据来自每份报告的 _novelty）。"""
    from datetime import datetime as _dt, timedelta as _td
    from app.models.report import Report

    since = _dt.utcnow() - _td(days=days)
    rows = db.query(Report).filter(Report.created_at >= since).all()
    daily: dict[str, dict] = {}
    totals = {"reports": 0, "fresh": 0, "progress": 0, "repeat": 0,
              "zero_update": 0, "digest": 0, "skipped": 0}
    for r in rows:
        try:
            decision = json.loads(r.decision_json) if r.decision_json else {}
        except (ValueError, TypeError):
            decision = {}
        nov = (decision or {}).get("_novelty")
        if nov:
            day = str(r.created_at)[:10]
            slot = daily.setdefault(day, {"date": day, "fresh": 0, "progress": 0, "repeat": 0, "digest": 0})
            for k in ("fresh", "progress", "repeat"):
                slot[k] += int(nov.get(k) or 0)
            if nov.get("mode") == "digest":
                slot["digest"] += 1
                totals["digest"] += 1
            totals["reports"] += 1
            for k in ("fresh", "progress", "repeat"):
                totals[k] += int(nov.get(k) or 0)
            if not (nov.get("fresh") or nov.get("progress")):
                totals["zero_update"] += 1
        elif r.status == "skipped":
            totals["skipped"] += 1

    series = []
    for day in sorted(daily):
        s = daily[day]
        denom = s["fresh"] + s["progress"] + s["repeat"]
        s["dedupe_rate"] = round(s["repeat"] / denom * 100, 1) if denom else 0.0
        p_denom = s["progress"] + s["repeat"]
        s["progress_rate"] = round(s["progress"] / p_denom * 100, 1) if p_denom else 0.0
        series.append(s)

    denom = totals["fresh"] + totals["progress"] + totals["repeat"]
    p_denom = totals["progress"] + totals["repeat"]
    totals["dedupe_rate"] = round(totals["repeat"] / denom * 100, 1) if denom else 0.0
    totals["progress_rate"] = round(totals["progress"] / p_denom * 100, 1) if p_denom else 0.0
    return {"days": days, "totals": totals, "daily": series}

@router.get("/ai-models")
async def list_ai_models(admin: User = Depends(get_admin_user), db: Session = Depends(get_db)):
    """按当前保存的 AI 配置，从服务商拉取可选模型列表（模型名自动获取）。"""
    cfg = {c.key.replace("ai_", ""): c.value for c in db.query(SystemConfig).filter(SystemConfig.key.like("ai_%")).all()}
    api_key = cfg.get("api_key") or ""
    base_url = (cfg.get("base_url") or "https://api.deepseek.com").rstrip("/")
    if not api_key:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "请先保存 AI API Key")
    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        data = await client.models.list()
        return {"models": [m.id for m in data.data], "current": cfg.get("model", "")}
    except Exception as e:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"获取模型列表失败（{type(e).__name__}），请核对配置")

@router.get("/metrics/feedback")
async def feedback_metrics(days: int = Query(30, ge=1, le=180),
                           admin: User = Depends(get_admin_user),
                           db: Session = Depends(get_db)):
    """反馈分布：有用/没用、原因占比、按天趋势。"""
    from datetime import datetime as _dt, timedelta as _td
    from app.models.report_feedback import ReportFeedback
    since = _dt.utcnow() - _td(days=days)
    rows = db.query(ReportFeedback).filter(ReportFeedback.created_at >= since).all()
    labels = {"direction": "方向不相关", "shallow": "太浅", "stale": "太旧或重复",
              "evidence": "依据不足", "length": "太长或太频繁"}
    up = sum(1 for r in rows if r.value == "up")
    down = sum(1 for r in rows if r.value == "down")
    reasons: dict[str, int] = {}
    daily: dict[str, dict] = {}
    for r in rows:
        day = str(r.created_at)[:10]
        slot = daily.setdefault(day, {"date": day, "up": 0, "down": 0})
        slot[r.value] = slot.get(r.value, 0) + 1
        if r.value == "down":
            key = (getattr(r, "reason", None) or "unknown")
            reasons[key] = reasons.get(key, 0) + 1
    reason_list = [{"key": k, "label": labels.get(k, "未归因"), "count": v}
                   for k, v in sorted(reasons.items(), key=lambda x: -x[1])]
    return {
        "days": days,
        "totals": {"up": up, "down": down, "total": up + down,
                   "useful_rate": round(up / (up + down) * 100, 1) if (up + down) else None},
        "reasons": reason_list,
        "daily": [daily[d] for d in sorted(daily)],
    }
