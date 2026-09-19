"""
FastAPI 应用入口
"""

from __future__ import annotations
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.middleware import RateLimitMiddleware, SecurityHeadersMiddleware, AntiBotMiddleware

from app.config import get_settings
from app.api.router import api_router

settings = get_settings()

# ── 全局时间序列化：数据库 naive datetime 一律按 UTC 输出（前端才能正确显示北京时间）──
import datetime as _dt
from fastapi.encoders import ENCODERS_BY_TYPE as _ENC

def _utc_iso(o):
    if getattr(o, "tzinfo", None) is None:
        o = o.replace(tzinfo=_dt.timezone.utc)
    return o.isoformat()

_ENC[_dt.datetime] = _utc_iso


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 本地调度器：开发/单机模式启用；生产 Celery 模式（ENABLE_LOCAL_SCHEDULER=false）关闭，
    # 避免与 Celery beat 双重派发（文件锁防多 worker，但不能跨进程体系互斥）
    if settings.enable_local_scheduler:
        from app.services.local_scheduler import start_local_scheduler
        start_local_scheduler()
    yield
    if settings.enable_local_scheduler:
        from app.services.local_scheduler import stop_local_scheduler
        stop_local_scheduler()


app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    lifespan=lifespan,
)

# Security middlewares (order matters)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(AntiBotMiddleware)
app.add_middleware(SecurityHeadersMiddleware)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")


@app.get("/health")
async def health_check():
    return {"status": "ok", "app": settings.app_name}


@app.get("/api/v1/public/demo-report")
async def public_demo_report():
    """公开演示报告"""
    from app.database import SessionLocal
    from app.models.report import Report
    from app.models.news_source import NewsSource
    db = SessionLocal()
    try:
        latest = db.query(Report).filter(
            Report.status == "sent", Report.ai_analysis_html.isnot(None)
        ).order_by(Report.created_at.desc()).first()
        if not latest:
            return {"found": False, "subject": "", "ai_html": "", "news_items": [], "sources": []}

        news = []
        if latest.raw_news_json:
            import json
            news = json.loads(latest.raw_news_json)[:5]

        sources = db.query(NewsSource).filter(NewsSource.is_active == True).all()

        return {
            "found": True,
            "subject": latest.subject or "",
            "ai_html": latest.ai_analysis_html or "",
            "news_items": news,
            "sources": [s.name for s in sources],
            "created_at": latest.created_at.replace(tzinfo=_dt.timezone.utc).isoformat() if latest.created_at else "",
        }
    finally:
        db.close()


@app.get("/api/v1/public/icp")
async def public_icp():
    """公开备案/合规文本"""
    from app.database import SessionLocal
    from app.models.compliance_text import ComplianceText
    db = SessionLocal()
    try:
        texts = {c.key: c.content for c in db.query(ComplianceText).all()}
        return {
            "icp_record": texts.get("icp_record", ""),
            "privacy_policy": texts.get("privacy_policy", ""),
            "disclaimer": texts.get("disclaimer", ""),
        }
    finally:
        db.close()


@app.get("/api/v1/public/ai-default")
async def public_ai_default():
    """公开 AI 默认配置（隐藏 Key 敏感信息）"""
    from app.database import SessionLocal
    from app.models.system_config import SystemConfig
    db = SessionLocal()
    try:
        cfgs = {c.key: c.value for c in db.query(SystemConfig).filter(SystemConfig.key.in_(
            ["ai_provider", "ai_api_key", "ai_base_url", "ai_model", "ai_enabled"]
        )).all()}
        provider = cfgs.get("ai_provider") or settings.ai_default_provider
        model = cfgs.get("ai_model") or settings.deepseek_model or settings.volcano_model or "默认"
        base_url = cfgs.get("ai_base_url") or (
            settings.deepseek_base_url if settings.ai_default_provider == "deepseek" else settings.volcano_base_url
        )
        enabled = cfgs.get("ai_enabled", str(settings.ai_enabled)).lower() in ("true", "1", "yes")
        has_key = bool(cfgs.get("ai_api_key") or settings.deepseek_api_key or settings.volcano_api_key)
        return {"provider": provider, "model": model, "base_url": base_url,
                "enabled": enabled, "has_key": has_key}
    finally:
        db.close()