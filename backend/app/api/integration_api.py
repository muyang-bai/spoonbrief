"""一勺热点接收 AiLifeOS 的统一画像与事件（HMAC 服务间鉴权）。

- POST /api/v1/internal/profile/sync  {uid, profile, profile_version}
- POST /api/v1/hooks/ailifeos        {event_id, type, uid, data...}
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import Column, DateTime, Integer, String, Text, text
from sqlalchemy.orm import Session

from app.database import Base, get_db

router = APIRouter(prefix="/api/v1", tags=["integration"])

_SEEN: dict[str, float] = {}


class UnifiedProfile(Base):
    __tablename__ = "hb_unified_profiles"

    user_id = Column(Integer, primary_key=True)
    ailifeos_uid = Column(String(64), nullable=True, index=True)
    payload = Column(Text, nullable=False, default="{}")
    version = Column(Integer, nullable=False, default=0)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


async def verify_integration(request: Request) -> bool:
    secret = os.getenv("INTEGRATION_HMAC_SECRET") or os.getenv("HOTBRIEF_HMAC_SECRET") or ""
    if not secret:
        raise HTTPException(status_code=503, detail="integration secret not configured")
    headers = request.headers
    timestamp = headers.get("x-timestamp")
    nonce = headers.get("x-nonce")
    signature = headers.get("x-signature", "")
    if not timestamp or not nonce or not signature:
        raise HTTPException(status_code=401, detail="missing signature headers")
    try:
        ts = int(timestamp)
    except ValueError:
        raise HTTPException(status_code=401, detail="bad timestamp")
    if abs(time.time() - ts) > 300:
        raise HTTPException(status_code=401, detail="signature expired")
    body = await request.body()
    canonical = f"{request.method.upper()}\n{request.url.path}\n{timestamp}\n{nonce}\n{_sha(body)}"
    expected = hmac.new(secret.encode(), canonical.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature):
        raise HTTPException(status_code=401, detail="bad signature")
    now = time.time()
    for key, seen in list(_SEEN.items()):
        if now - seen > 600:
            _SEEN.pop(key, None)
    if nonce in _SEEN:
        raise HTTPException(status_code=401, detail="nonce replay")
    _SEEN[nonce] = now
    return True


def _link_user(db: Session, uid: str | None, email: str | None) -> int | None:
    """按邮箱或已存映射找到一勺热点用户 id。"""
    if email:
        row = db.execute(text("SELECT id FROM hb_users WHERE email=:email LIMIT 1"), {"email": email}).first()
        if row:
            return int(row[0])
    if uid:
        row = db.execute(
            text("SELECT user_id FROM ailifeos_links WHERE ailifeos_uid=:uid LIMIT 1"), {"uid": uid}
        ).first()
        if row:
            return int(row[0])
    return None


@router.post("/internal/profile/sync")
async def profile_sync(request: Request, db: Session = Depends(get_db), _: bool = Depends(verify_integration)):
    body = await request.json()
    uid = str(body.get("uid") or "")
    profile = body.get("profile") or {}
    version = int(body.get("profile_version") or 0)
    email = str((profile.get("email") if isinstance(profile, dict) else "") or "")
    user_id = _link_user(db, uid, email)
    if user_id is None:
        return {"ok": False, "error": {"code": "UNLINKED", "message": "没有匹配的一勺热点账号。"}}

    row = db.query(UnifiedProfile).filter(UnifiedProfile.user_id == user_id).first()
    if row is None:
        row = UnifiedProfile(user_id=user_id, ailifeos_uid=uid or None, payload="{}", version=0)
        db.add(row)
    row.payload = json.dumps(profile, ensure_ascii=False)
    row.version = version
    row.ailifeos_uid = uid or row.ailifeos_uid
    link = db.execute(text("SELECT 1 FROM ailifeos_links WHERE user_id=:id"), {"id": user_id}).first()
    if link:
        db.execute(
            text("UPDATE ailifeos_links SET ailifeos_uid=:uid, sync_enabled=1, updated_at=NOW() WHERE user_id=:id"),
            {"uid": uid, "id": user_id},
        )
    else:
        db.execute(
            text("INSERT INTO ailifeos_links(user_id, ailifeos_uid, sync_enabled, updated_at) VALUES(:id,:uid,1,NOW())"),
            {"id": user_id, "uid": uid},
        )
    db.commit()
    return {"ok": True, "data": {"user_id": user_id, "profile_version": version}}


@router.post("/hooks/ailifeos")
async def hooks(request: Request, db: Session = Depends(get_db), _: bool = Depends(verify_integration)):
    body = await request.json()
    uid = str(body.get("uid") or "")
    kind = str(body.get("type") or "")
    data = body.get("data") or {}
    tier = str((data.get("tier") if isinstance(data, dict) else "") or "")
    if uid and tier:
        db.execute(
            text("UPDATE ailifeos_links SET tier=:tier, updated_at=NOW() WHERE ailifeos_uid=:uid"),
            {"tier": tier, "uid": uid},
        )
        db.commit()
    return {"ok": True, "accepted": kind}


# ---------- 订阅（与网站新建订阅同表同字段） ----------
def _uid_user(db: Session, uid: str | None, email: str | None) -> int | None:
    if uid:
        row = db.execute(text("SELECT user_id FROM ailifeos_links WHERE ailifeos_uid=:uid LIMIT 1"), {"uid": uid}).first()
        if row:
            return int(row[0])
    if email:
        row = db.execute(text("SELECT id FROM hb_users WHERE email=:email LIMIT 1"), {"email": email}).first()
        if row:
            return int(row[0])
    return None


def _mobile_owner(db, uid, external_id=None):
    # Only a server-supplied AiLifeOS link, never an email supplied by the mobile client.
    user_id = _uid_user(db, uid, None) if uid else None
    # external_id is asserted only by the HMAC-authenticated gateway from its own integration_links.
    # This supports established AiLifeOS links whose reverse profile-sync link has not been created.
    if external_id is not None:
        if not str(external_id).isdigit() or int(external_id) <= 0 or not uid:
            raise HTTPException(409, "账号关联编号无效")
        if user_id is not None and user_id != int(external_id):
            raise HTTPException(409, "两端账号关联不一致，请重新关联")
        user_id = int(external_id)
    if user_id is None:
        raise HTTPException(409, "尚未关联一勺热点账号，请先使用已关联账号登录")
    from app.models.user import User
    user = db.get(User, user_id)
    if not user or not user.is_active:
        raise HTTPException(403, "账号不可用")
    return user


def _mobile_sub(row):
    from app.schemas.subscription import SubscriptionOut
    return SubscriptionOut.model_validate(row).model_dump(mode="json")


@router.get("/internal/subscriptions")
async def list_subscriptions(request: Request, db: Session = Depends(get_db), _: bool = Depends(verify_integration)):
    from app.models.subscription import Subscription
    from app.models.prompt_template import PromptTemplate
    from app.services.prompt_engine import template_accessible
    user = _mobile_owner(db, request.query_params.get("uid"), request.query_params.get("external_id"))
    rows = db.query(Subscription).filter(Subscription.user_id == user.id).order_by(Subscription.id.desc()).all()
    templates = [{"id": t.id, "name": t.name} for t in db.query(PromptTemplate).all() if template_accessible(t, user.id)]
    return {"ok": True, "data": {"items": [_mobile_sub(r) for r in rows], "templates": templates}}


MOBILE_FIELDS = {"name", "keywords", "time_window", "cron_expr", "timezone", "ai_analysis", "prompt_template_id", "is_active"}


async def _mobile_save(request, db, creating):
    from app.models.subscription import Subscription
    from app.schemas.subscription import SubscriptionCreate, SubscriptionUpdate
    from app.api import subscriptions as web
    from pydantic import ValidationError
    body = await request.json()
    user = _mobile_owner(db, body.get("uid"), body.get("external_id"))
    patch = {k: v for k, v in body.items() if k in MOBILE_FIELDS}
    try:
        if creating:
            patch.pop("is_active", None)
            row = await web.create_subscription(SubscriptionCreate(**patch), user, db)
        else:
            sid = body.get("id")
            if not isinstance(sid, int) or isinstance(sid, bool):
                raise HTTPException(400, "缺少有效订阅编号")
            row = db.query(Subscription).filter(Subscription.id == sid, Subscription.user_id == user.id).first()
            if row is None:
                raise HTTPException(404, "订阅不存在")
            expected = body.get("expected") or {}
            if not isinstance(expected, dict):
                raise HTTPException(400, "订阅版本格式错误")
            if any(k in expected and getattr(row, k) != expected[k] for k in patch):
                raise HTTPException(409, "网页上的订阅已变化，请先刷新再合并修改；本次草稿未保存")
            row = await web.update_subscription(sid, SubscriptionUpdate(**patch), user, db)
    except HTTPException:
        db.rollback()
        raise
    except ValidationError:
        db.rollback()
        raise HTTPException(400, "订阅字段无效，请检查名称、时间窗和发送时间")
    return {"ok": True, "data": {"item": _mobile_sub(row)}}


@router.post("/internal/subscriptions")
async def create_subscription(request: Request, db: Session = Depends(get_db), _: bool = Depends(verify_integration)):
    return await _mobile_save(request, db, True)


@router.put("/internal/subscriptions")
async def update_subscription(request: Request, db: Session = Depends(get_db), _: bool = Depends(verify_integration)):
    return await _mobile_save(request, db, False)


def _report_row(row, detail=False):
    from bs4 import BeautifulSoup
    from datetime import timezone
    def plain(value):
        soup = BeautifulSoup(value or "", "html.parser")
        for node in soup(["script", "style", "head"]):
            node.decompose()
        return soup.get_text("\n", strip=True)
    published = row.sent_at or row.created_at
    stamp = published.replace(tzinfo=timezone.utc) if published.tzinfo is None else published
    out = {"report_id": str(row.id), "title": row.subject or "订阅简报", "created_at": int(stamp.timestamp() * 1000), "summary": "已生成的订阅简报，点开查看完整分析。"}
    if detail:
        try:
            decision = json.loads(row.decision_json or "{}")
        except (ValueError, TypeError):
            decision = {}
        try:
            news = json.loads(row.raw_news_json or "[]")
        except (ValueError, TypeError):
            news = []
        decision = decision if isinstance(decision, dict) else {}
        news = news if isinstance(news, list) else []
        quality = decision.get("_quality") or {}
        quality = quality if isinstance(quality, dict) else {}
        fresh = decision.get("_freshness") or {}
        fresh = fresh if isinstance(fresh, dict) else {}
        out.update(body=plain(row.ai_analysis_html), sources=[{k: str(n.get(k) or "") for k in ("title", "source", "link", "published")} for n in news if isinstance(n, dict)], quality=quality, freshness=fresh, analyst=quality.get("template_name") or "历史报告未记录分析师名称")
    return out


@router.get("/internal/reports")
async def mobile_reports(request: Request, db: Session = Depends(get_db), _: bool = Depends(verify_integration)):
    from app.models.report import Report
    from sqlalchemy import func
    user = _mobile_owner(db, request.query_params.get("uid"), request.query_params.get("external_id"))
    try:
        offset = max(0, int(request.query_params.get("offset", "0")))
    except ValueError:
        raise HTTPException(400, "分页无效")
    rows = db.query(Report).filter(Report.user_id == user.id, Report.status == "sent").order_by(func.coalesce(Report.sent_at, Report.created_at).desc(), Report.id.desc()).offset(offset).limit(51).all()
    return {"ok": True, "data": {"linked": True, "reason": "ok" if rows else "empty", "briefs": [_report_row(r) for r in rows[:50]], "nextOffset": offset + 50 if len(rows) > 50 else None}}


@router.get("/internal/reports/{report_id}")
async def mobile_report(report_id: int, request: Request, db: Session = Depends(get_db), _: bool = Depends(verify_integration)):
    from app.models.report import Report
    user = _mobile_owner(db, request.query_params.get("uid"), request.query_params.get("external_id"))
    row = db.query(Report).filter(Report.user_id == user.id, Report.id == report_id, Report.status == "sent").first()
    if row is None:
        raise HTTPException(404, "这份简报不存在或当前账号无权读取")
    return {"ok": True, "data": {"report": _report_row(row, True)}}


# ---------- 账号密码校验（供 AiLifeOS 复用同一套账号信息） ----------
@router.post("/internal/accounts/verify")
async def verify_account(request: Request, db: Session = Depends(get_db), _: bool = Depends(verify_integration)):
    body = await request.json()
    email = str(body.get("email") or "").strip().lower()
    password = str(body.get("password") or "")
    if not email or not password:
        return {"ok": False, "error": {"code": "INVALID_ARGUMENT", "message": "需要邮箱和密码。"}}
    from app.models.user import User
    from app.utils.security import verify_password
    user = db.query(User).filter(User.email == email).first()
    if user is None or not verify_password(password, user.password_hash):
        return {"ok": False, "error": {"code": "INVALID_CREDENTIALS", "message": "邮箱或密码不正确。"}}
    if not user.is_active:
        return {"ok": False, "error": {"code": "ACCOUNT_DISABLED", "message": "账号已停用。"}}
    user.last_login_at = __import__("datetime").datetime.utcnow()
    db.commit()
    return {"ok": True, "data": {"id": user.id, "email": user.email, "nickname": user.nickname, "role": getattr(user.role, "value", user.role)}}
