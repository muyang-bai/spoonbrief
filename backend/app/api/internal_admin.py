"""一勺热点 -> AiLifeOS 统一后台的内部管理接口。

鉴权：HMAC-SHA256，规范串 `METHOD\\nPATH\\nTIMESTAMP\\nNONCE\\nsha256(BODY)`，
请求头 X-Client-Id / X-Timestamp / X-Nonce / X-Signature；管理端另带 X-Admin-Id / X-Admin-Role。
不返回任何密码或 API Key 明文。
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.utils import secrets as secrets_util
from app.models.ailifeos_link import AilifeosLink
from app.models.announcement import Announcement
from app.models.keyword_stat import KeywordStat
from app.models.news_source import NewsSource
from app.models.prompt_template import PromptTemplate
from app.models.report import Report
from app.models.subscription import Subscription
from app.models.system_config import SystemConfig
from app.models.token_usage import TokenUsage
from app.models.user import User

router = APIRouter(prefix="/internal/admin/v1", tags=["internal-admin"])

_SEEN: dict[str, float] = {}
SECRET_MASK = "********"
OFFICIAL_MODELS = ("deepseek-flash", "deepseek-v4-pro")
MODEL_ALIASES = {"deepseek-v4-flash": "deepseek-flash", "deepseek-pro": "deepseek-v4-pro"}


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _mask(value: str | None) -> str:
    if not value:
        return "未设置"
    return SECRET_MASK + value[-4:] if len(value) > 8 else SECRET_MASK


async def verify_hmac(request: Request) -> bool:
    secret = os.getenv("ADMIN_HMAC_SECRET") or os.getenv("INTEGRATION_HMAC_SECRET") or ""
    if not secret:
        raise HTTPException(status_code=503, detail="admin secret not configured")
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
    canonical = f"{request.method.upper()}\n{request.url.path}\n{timestamp}\n{nonce}\n{_sha256(body)}"
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


def _bj(dt: datetime | None) -> str | None:
    return dt.isoformat() if dt else None


def _cfg(db: Session, key: str) -> str | None:
    row = db.query(SystemConfig).filter(SystemConfig.key == key).first()
    return row.value if row else None


def _cfg_map(db: Session, prefix: str) -> dict[str, str]:
    rows = db.query(SystemConfig).filter(SystemConfig.key.like(prefix + "%")).all()
    return {c.key[len(prefix):]: (c.value if c.value is not None else "") for c in rows}


def _set_cfg(db: Session, key: str, value: str) -> None:
    row = db.query(SystemConfig).filter(SystemConfig.key == key).first()
    if row:
        row.value = value
    else:
        db.add(SystemConfig(key=key, value=value))


def _keep_secret(db: Session, key: str, incoming) -> str:
    if incoming is None or str(incoming) == "" or str(incoming).startswith(SECRET_MASK) or secrets_util.masked(str(incoming)):
        return _cfg(db, key) or ""
    return secrets_util.seal(str(incoming))


def _parse_json(raw: str | None):
    if not raw:
        return None
    try:
        return json.loads(raw)
    except Exception:
        return None


def _last_test(db: Session, kind: str):
    return _parse_json(_cfg(db, f"lasttest:{kind}"))


def _record_test(db: Session, kind: str, ok: bool, message: str) -> None:
    val = json.dumps({"ok": ok, "message": (message or "")[:300], "at": datetime.utcnow().isoformat() + "Z"}, ensure_ascii=False)
    try:
        db.rollback()
        _set_cfg(db, f"lasttest:{kind}", val)
        db.commit()
    except Exception:
        db.rollback()


async def _json_body(request: Request) -> dict:
    raw = await request.body()
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except Exception:
        raise HTTPException(status_code=400, detail="invalid json")
    return data if isinstance(data, dict) else {}


def _quota_label(remaining) -> str:
    if remaining is None:
        return ""
    try:
        n = int(remaining)
    except (TypeError, ValueError):
        return ""
    if n < 0:
        return "不限"
    return str(n)


def _permission(role) -> str:
    raw = role.value if hasattr(role, "value") else str(role or "")
    return "admin" if raw.upper() == "ADMIN" or raw.lower() == "admin" else "member"


@router.get("/stats/overview")
def stats_overview(db: Session = Depends(get_db), _: bool = Depends(verify_hmac)):
    now = datetime.utcnow()
    since = now - timedelta(hours=24)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    users = db.query(func.count(User.id)).scalar() or 0
    active_users = db.query(func.count(User.id)).filter(User.is_active.is_(True)).scalar() or 0
    linked = db.query(func.count(AilifeosLink.user_id)).scalar() or 0
    subs_total = db.query(func.count(Subscription.id)).scalar() or 0
    subs_active = db.query(func.count(Subscription.id)).filter(Subscription.is_active.is_(True)).scalar() or 0
    reports_total = db.query(func.count(Report.id)).scalar() or 0
    reports_today = db.query(func.count(Report.id)).filter(Report.created_at >= today_start).scalar() or 0
    reports_24h = db.query(func.count(Report.id)).filter(Report.created_at >= since).scalar() or 0
    failed_24h = db.query(func.count(Report.id)).filter(Report.created_at >= since, Report.status == "failed").scalar() or 0
    sent = db.query(func.count(Report.id)).filter(Report.status == "sent").scalar() or 0
    tokens_24h = db.query(func.coalesce(func.sum(TokenUsage.total_tokens), 0)).filter(TokenUsage.created_at >= since).scalar() or 0
    cost_24h = db.query(func.coalesce(func.sum(TokenUsage.cost_yuan), 0)).filter(TokenUsage.created_at >= since).scalar() or 0
    top_model = (
        db.query(TokenUsage.model, func.sum(TokenUsage.total_tokens))
        .filter(TokenUsage.created_at >= since, TokenUsage.model.isnot(None))
        .group_by(TokenUsage.model)
        .order_by(func.sum(TokenUsage.total_tokens).desc())
        .first()
    )
    cfg_model = _cfg(db, "ai_model") or _cfg(db, "ai_model") or os.getenv("DEEPSEEK_MODEL")
    ai_map = _cfg_map(db, "ai_")
    model = (top_model[0] if top_model and top_model[0] else None) or ai_map.get("model") or cfg_model or "deepseek-flash"
    model = MODEL_ALIASES.get(model, model)
    delivery = round(sent / reports_total * 100, 2) if reports_total else 0.0
    return {
        "users": int(users),
        "active_users": int(active_users),
        "linked_users": int(linked),
        "subscriptions_total": int(subs_total),
        "subscriptions_active": int(subs_active),
        "subscriptions": int(subs_active),
        "reports_total": int(reports_total),
        "reports_today": int(reports_today),
        "reports_24h": int(reports_24h),
        "failed_24h": int(failed_24h),
        "emails_sent": int(sent),
        "email_delivery_rate": delivery,
        "tokens_24h": int(tokens_24h),
        "cost_yuan_24h": round(float(cost_24h), 4),
        "model": model,
    }


@router.get("/stats/user-growth")
def stats_user_growth(days: int = 30, db: Session = Depends(get_db), _: bool = Depends(verify_hmac)):
    days = max(1, min(int(days or 30), 180))
    since = datetime.utcnow() - timedelta(days=days - 1)
    rows = (
        db.query(func.date(User.created_at).label("d"), func.count(User.id))
        .filter(User.created_at >= since)
        .group_by(func.date(User.created_at))
        .order_by(func.date(User.created_at))
        .all()
    )
    counts = {str(r[0]): int(r[1]) for r in rows}
    items = []
    total = int(db.query(func.count(User.id)).filter(User.created_at < since).scalar() or 0)
    for i in range(days):
        day = (since + timedelta(days=i)).date().isoformat()
        new = counts.get(day, 0)
        total += new
        items.append({"day": day, "new": new, "total": total})
    return {"items": items}


def _smtp_payload(db: Session) -> dict:
    c = _cfg_map(db, "smtp_")
    host = c.get("host") or os.getenv("SMTP_HOST") or ""
    port = c.get("port") or os.getenv("SMTP_PORT") or ""
    user = c.get("user") or os.getenv("SMTP_USER") or ""
    password = c.get("password") or os.getenv("SMTP_PASSWORD") or ""
    return {
        "host": host,
        "port": int(port) if str(port).isdigit() else (port or None),
        "user": user,
        "password": _mask(secrets_util.unseal(password)),
        "from_email": c.get("from_email") or os.getenv("SMTP_FROM_EMAIL") or "",
        "from_name": c.get("from_name") or os.getenv("SMTP_FROM_NAME") or "一勺热点",
        "use_ssl": (c.get("use_ssl") or os.getenv("SMTP_USE_SSL") or "True"),
        "last_test": _last_test(db, "smtp"),
    }


def _ai_payload(db: Session) -> dict:
    c = _cfg_map(db, "ai_")
    model = MODEL_ALIASES.get(c.get("model") or "", c.get("model") or os.getenv("DEEPSEEK_MODEL") or "")
    return {
        "provider": c.get("provider") or os.getenv("AI_DEFAULT_PROVIDER") or "deepseek",
        "base_url": c.get("base_url") or os.getenv("DEEPSEEK_BASE_URL") or "",
        "model": model,
        "api_key": _mask(secrets_util.unseal(c.get("api_key")) or os.getenv("DEEPSEEK_API_KEY") or ""),
        "enabled": c.get("enabled") or os.getenv("AI_ENABLED") or "",
        "last_test": _last_test(db, "ai"),
    }


@router.get("/smtp")
def smtp_config(db: Session = Depends(get_db), _: bool = Depends(verify_hmac)):
    return _smtp_payload(db)


@router.put("/smtp")
async def update_smtp(request: Request, db: Session = Depends(get_db), _: bool = Depends(verify_hmac)):
    body = await _json_body(request)
    allowed = ("host", "port", "user", "password", "from_email", "from_name", "use_ssl")
    for k in allowed:
        if k not in body:
            continue
        v = body[k]
        if k == "password":
            v = _keep_secret(db, "smtp_password", v)
        _set_cfg(db, f"smtp_{k}", "" if v is None else str(v))
    db.commit()
    return _smtp_payload(db)


@router.post("/smtp/test")
async def smtp_test(request: Request, db: Session = Depends(get_db), _: bool = Depends(verify_hmac)):
    body = await _json_body(request)
    c = _cfg_map(db, "smtp_")
    if not (c.get("host") or os.getenv("SMTP_HOST")):
        msg = "请先保存 SMTP 配置后再测试连接"
        _record_test(db, "smtp", False, msg)
        return {"ok": False, "message": msg}
    to = str(body.get("to") or c.get("from_email") or os.getenv("SMTP_FROM_EMAIL") or "").strip()
    if not to:
        msg = "没有可用的测试收件邮箱"
        _record_test(db, "smtp", False, msg)
        return {"ok": False, "message": msg}
    try:
        from app.services.email_sender import send_email
        ok = await send_email(
            [to],
            "一勺热点 - SMTP测试邮件",
            "<h3>SMTP连接测试成功！</h3><p>如果你收到这封邮件，说明 SMTP 配置可用。</p>",
            from_email=c.get("from_email") or os.getenv("SMTP_FROM_EMAIL"),
            from_name=c.get("from_name") or os.getenv("SMTP_FROM_NAME") or "一勺热点",
        )
        msg = f"测试邮件已发送至 {to}，请检查收件箱" if ok else "SMTP 连接失败，请检查配置"
        _record_test(db, "smtp", bool(ok), msg)
        return {"ok": bool(ok), "message": msg}
    except Exception as e:  # noqa: BLE001
        msg = f"SMTP 测试失败：{str(e)[:200]}"
        _record_test(db, "smtp", False, msg)
        return {"ok": False, "message": msg}


@router.get("/ai-config")
def ai_config(db: Session = Depends(get_db), _: bool = Depends(verify_hmac)):
    return _ai_payload(db)


@router.put("/ai-config")
async def update_ai(request: Request, db: Session = Depends(get_db), _: bool = Depends(verify_hmac)):
    body = await _json_body(request)
    allowed = ("provider", "base_url", "model", "api_key", "enabled")
    for k in allowed:
        if k not in body:
            continue
        v = body[k]
        if k == "api_key":
            v = _keep_secret(db, "ai_api_key", v)
        if k == "model" and isinstance(v, str):
            v = MODEL_ALIASES.get(v.strip(), v.strip())
            if v and v not in OFFICIAL_MODELS:
                raise HTTPException(status_code=422, detail="不支持的模型，请选择当前官方模型")
            if v:
                _set_cfg(db, "ai_model", str(v))
        _set_cfg(db, f"ai_{k}", "" if v is None else str(v))
    db.commit()
    return _ai_payload(db)


@router.post("/ai-config/test")
async def ai_test(db: Session = Depends(get_db), _: bool = Depends(verify_hmac)):
    c = _cfg_map(db, "ai_")
    api_key = secrets_util.unseal(c.get("api_key")) or os.getenv("DEEPSEEK_API_KEY") or ""
    if not api_key:
        msg = "请先保存 AI 配置后再测试连接"
        _record_test(db, "ai", False, msg)
        return {"ok": False, "message": msg}
    model = MODEL_ALIASES.get(c.get("model") or "", c.get("model") or os.getenv("DEEPSEEK_MODEL") or "deepseek-flash")
    if model not in OFFICIAL_MODELS:
        model = "deepseek-flash"
    base_url = c.get("base_url") or os.getenv("DEEPSEEK_BASE_URL") or "https://api.deepseek.com"
    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        resp = await client.chat.completions.create(model=model, messages=[{"role": "user", "content": "OK"}], max_tokens=10)
        text = (resp.choices[0].message.content or "").strip()
        msg = f"连接成功，模型 {model} 已应答" + (f"：{text[:40]}" if text else "")
        _record_test(db, "ai", True, msg)
        return {"ok": True, "message": msg}
    except Exception as e:  # noqa: BLE001
        msg = f"连接失败：{str(e)[:200]}"
        _record_test(db, "ai", False, msg)
        return {"ok": False, "message": msg}


@router.get("/announcements")
def announcements(db: Session = Depends(get_db), _: bool = Depends(verify_hmac)):
    rows = db.query(Announcement).order_by(Announcement.created_at.desc()).limit(50).all()
    return {
        "items": [
            {
                "id": a.id,
                "title": a.title,
                "published_at": _bj(a.published_at),
                "offline_at": _bj(getattr(a, "erased_at", None)),
            }
            for a in rows
        ]
    }


@router.put("/announcements/{aid}/offline")
def announcement_offline(aid: int, db: Session = Depends(get_db), _: bool = Depends(verify_hmac)):
    a = db.query(Announcement).filter(Announcement.id == aid).first()
    if not a:
        raise HTTPException(status_code=404, detail="公告不存在")
    a.erased_at = datetime.utcnow()
    db.commit()
    return {"id": a.id, "title": a.title, "published_at": _bj(a.published_at), "offline_at": _bj(a.erased_at)}


@router.get("/users")
def users(db: Session = Depends(get_db), _: bool = Depends(verify_hmac)):
    rows = (
        db.query(User, AilifeosLink)
        .outerjoin(AilifeosLink, AilifeosLink.user_id == User.id)
        .order_by(User.id)
        .limit(500)
        .all()
    )
    items = []
    for u, link in rows:
        permission = _permission(u.role)
        stored = (link.tier if link else None) or None
        items.append(
            {
                "id": u.id,
                "email": u.email,
                "nickname": u.nickname,
                "is_active": bool(u.is_active),
                "permission": permission,
                "role": permission,
                "ailifeos_uid": link.ailifeos_uid if link else None,
                "tier": stored,
                "tier_synced": bool(stored),
                "sync_enabled": bool(link.sync_enabled) if link else False,
            }
        )
    return {"items": items}


@router.put("/users/{uid}")
async def update_user(uid: int, request: Request, db: Session = Depends(get_db), _: bool = Depends(verify_hmac)):
    body = await _json_body(request)
    u = db.query(User).filter(User.id == uid).first()
    if not u:
        raise HTTPException(status_code=404, detail="用户不存在")
    if "is_active" in body:
        u.is_active = bool(body["is_active"])
    db.commit()
    return {"id": u.id, "is_active": bool(u.is_active)}


@router.get("/topics")
def topics(db: Session = Depends(get_db), _: bool = Depends(verify_hmac)):
    """订阅主题热度：按订阅名称计数（条数，不是历史检索词频）。"""
    rows = (
        db.query(Subscription.name, func.count(Subscription.id), func.sum(Subscription.is_active.is_(True)))
        .group_by(Subscription.name)
        .order_by(func.count(Subscription.id).desc())
        .limit(100)
        .all()
    )
    return {"items": [{"name": n or "未命名", "subscribers": int(c or 0), "active": int(a or 0)} for n, c, a in rows], "metric": "subscription_count"}


@router.get("/keywords")
def keywords(db: Session = Depends(get_db), _: bool = Depends(verify_hmac)):
    """热门关键词：keyword_stats 的检索次数，不是当前订阅数。"""
    rows = db.query(KeywordStat).order_by(KeywordStat.search_count.desc()).limit(20).all()
    return {"items": [{"keyword": r.keyword, "count": int(r.search_count or 0), "updated_at": _bj(r.updated_at)} for r in rows], "metric": "search_count"}


@router.get("/sources")
def sources(db: Session = Depends(get_db), _: bool = Depends(verify_hmac)):
    rows = db.query(NewsSource).order_by(NewsSource.id).all()
    return {
        "items": [
            {
                "id": s.id,
                "name": s.name,
                "type": getattr(s.source_type, "value", s.source_type),
                "url": s.url,
                "credibility": s.credibility,
                "api_remaining": s.api_remaining,
                "api_remaining_label": _quota_label(s.api_remaining) or "—",
                "is_active": bool(s.is_active),
            }
            for s in rows
        ]
    }


@router.put("/sources/{sid}")
async def update_source(sid: int, request: Request, db: Session = Depends(get_db), _: bool = Depends(verify_hmac)):
    body = await _json_body(request)
    s = db.query(NewsSource).filter(NewsSource.id == sid).first()
    if not s:
        raise HTTPException(status_code=404, detail="信源不存在")
    if "is_active" in body:
        s.is_active = bool(body["is_active"])
    if "credibility" in body:
        try:
            s.credibility = int(body["credibility"])
        except (TypeError, ValueError):
            raise HTTPException(status_code=400, detail="可信度无效")
    db.commit()
    return {"id": s.id, "is_active": bool(s.is_active), "credibility": s.credibility}


@router.get("/token-usage")
def token_usage(days: int = 14, db: Session = Depends(get_db), _: bool = Depends(verify_hmac)):
    """近 N 天每日 Token（按北京时间分日；created_at 以 UTC 存储）。t110 · M7"""
    days = max(1, min(int(days or 14), 90))
    bj = timedelta(hours=8)
    today_bj = (datetime.utcnow() + bj).date()
    first_day = today_bj - timedelta(days=days - 1)
    since = datetime.combine(first_day, datetime.min.time()) - bj
    rows = (
        db.query(TokenUsage.created_at, TokenUsage.model, TokenUsage.total_tokens, TokenUsage.cost_yuan)
        .filter(TokenUsage.created_at >= since)
        .all()
    )
    agg: dict = {}
    for created_at, model, tokens, cost in rows:
        if not created_at:
            continue
        key = (str((created_at + bj).date()), model or "—")
        t, c = agg.get(key, (0, 0.0))
        agg[key] = (t + int(tokens or 0), c + float(cost or 0))
    return {
        "timezone": "Asia/Shanghai",
        "from": str(first_day),
        "to": str(today_bj),
        "items": [
            {"day": d, "model": m, "tokens": t, "cost_yuan": round(c, 4)}
            for (d, m), (t, c) in sorted(agg.items())
        ],
    }


@router.get("/email-templates")
def email_templates(db: Session = Depends(get_db), _: bool = Depends(verify_hmac)):
    rows = db.query(PromptTemplate).order_by(PromptTemplate.id).limit(100).all()
    return {
        "items": [
            {
                "id": t.id,
                "name": t.name,
                "model": t.model,
                "temperature": (t.temperature / 10 if t.temperature is not None else None),
                "is_default": bool(t.is_default),
                "is_active": bool(t.is_active),
            }
            for t in rows
        ]
    }


@router.put("/email-templates/{tid}")
async def update_template(tid: int, request: Request, db: Session = Depends(get_db), _: bool = Depends(verify_hmac)):
    body = await _json_body(request)
    t = db.query(PromptTemplate).filter(PromptTemplate.id == tid).first()
    if not t:
        raise HTTPException(status_code=404, detail="模板不存在")
    if body.get("is_default"):
        db.query(PromptTemplate).filter(PromptTemplate.is_default.is_(True)).update({"is_default": False})
        t.is_default = True
    if "is_active" in body:
        t.is_active = bool(body["is_active"])
    if "model" in body and body["model"]:
        t.model = str(body["model"])
    db.commit()
    return {"id": t.id, "is_default": bool(t.is_default), "is_active": bool(t.is_active), "model": t.model}


@router.get("/send-logs")
def send_logs(db: Session = Depends(get_db), _: bool = Depends(verify_hmac)):
    rows = (
        db.query(Report)
        .filter(Report.status.in_(["sent", "failed"]))
        .order_by(Report.created_at.desc())
        .limit(30)
        .all()
    )
    return {
        "items": [
            {"report_id": r.id, "user_id": r.user_id, "status": r.status, "error": r.error_message or ""}
            for r in rows
        ]
    }


@router.get("/audit")
def audit(_: bool = Depends(verify_hmac)):
    # 现网这一侧没有操作审计表，不编造记录。
    return {"items": [], "available": False, "note": "本侧未记录操作审计，统一后台自身的操作记录见「操作记录」页。"}


@router.get("/models")
def list_models(db: Session = Depends(get_db), _: bool = Depends(verify_hmac)):
    current = _cfg(db, "ai_model") or _cfg_map(db, "ai_").get("model") or ""
    current = MODEL_ALIASES.get(current, current)
    items = list(OFFICIAL_MODELS)
    if current and current not in items and current not in ("deepseek-chat", "deepseek-reasoner", "deepseek-pro"):
        items.append(current)
    return {"items": items, "current": current or None, "official": list(OFFICIAL_MODELS)}


@router.put("/config/model")
async def set_model(request: Request, db: Session = Depends(get_db), _: bool = Depends(verify_hmac)):
    body = await _json_body(request)
    model = MODEL_ALIASES.get(str(body.get("model") or "").strip(), str(body.get("model") or "").strip())
    if model not in OFFICIAL_MODELS:
        raise HTTPException(status_code=422, detail="不支持的模型，请选择当前官方模型")
    _set_cfg(db, "ai_model", model)
    db.commit()
    return {"model": model}
