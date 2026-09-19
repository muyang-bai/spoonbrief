"""Admin routes"""
import json, asyncio
from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import func, desc
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from app.database import get_db
from app.deps import get_admin_user
from app.models.user import User, UserRole
from app.models.subscription import Subscription
from app.models.report import Report
from app.models.news_source import NewsSource
from app.models.announcement import Announcement
from app.models.prompt_template import PromptTemplate
from app.models.keyword_stat import KeywordStat
from app.models.system_config import SystemConfig
from app.models.compliance_text import ComplianceText
from app.models.email_address import EmailAddress
from app.utils.security import hash_password
from app.config import get_settings
from app.schemas.admin import (
    AnnouncementOut, AnnouncementCreate,
    AdminUserOut, AdminUserUpdate,
    SmtpConfig, AiConfig,
    DashboardStats,
    ComplianceTextUpdate, ComplianceTextOut,
    PromptTemplateCreate, PromptTemplateOut,
)
from app.schemas.auth import RegisterRequest

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
            func.date_trunc("day", User.created_at).label("date"),
            func.count(User.id).label("count"),
        ).filter(User.created_at >= thirty_days_ago).group_by("date").order_by("date").all()
    user_growth = [{"date": str(d), "count": c} for d, c in growth]

    today_reports = db.query(func.count(Report.id)).filter(Report.created_at >= datetime.utcnow().replace(hour=0,minute=0,second=0)).scalar() or 0
    active_subs = db.query(func.count(Subscription.id)).filter(Subscription.is_active == True).scalar() or 0
    delivery_rate = round(sent_reports / total_reports * 100, 2) if total_reports > 0 else 0.0

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
        result.append(AdminUserOut(
            id=u.id, email=u.email, nickname=u.nickname, role=u.role.value if hasattr(u.role, 'value') else str(u.role),
            is_active=u.is_active, created_at=u.created_at, last_login_at=u.last_login_at,
            subscription_count=sub_count,
            api_quota_total=u.api_quota_total,
            api_quota_used=u.api_quota_used,
            api_quota_reset_at=u.api_quota_reset_at,
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
    api_key = cfg.get("api_key", "")
    if not api_key:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "请先保存AI配置后再测试连接")
    try:
        from openai import AsyncOpenAI
        base_url = cfg.get("base_url", "https://api.deepseek.com")
        model = cfg.get("model", "deepseek-v4-flash")
        client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        resp = await client.chat.completions.create(model=model, messages=[{"role":"user","content":"OK"}], max_tokens=10)
        return {"status": "ok", "message": f"连接成功！模型回复：{resp.choices[0].message.content.strip()}"}
    except Exception as e:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, f"连接失败：{str(e)[:200]}")


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