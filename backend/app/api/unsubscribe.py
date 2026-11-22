"""
退订路由（无需登录，通过 token 退订）
"""

from __future__ import annotations
from datetime import datetime

from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from loguru import logger

from app.database import get_db
from app.models.unsubscribe_token import UnsubscribeToken
from app.models.subscription import Subscription

router = APIRouter(prefix="/unsubscribe", tags=["admin"])

@router.get("", response_class=HTMLResponse)
async def unsubscribe_page(token: str, request: Request, db: Session = Depends(get_db)):
    """Handler"""
    record = db.query(UnsubscribeToken).filter(
        UnsubscribeToken.token == token,
        UnsubscribeToken.is_active == True,
    ).first()

    if not record:
        return HTMLResponse(content=_page("链接已失效", _INVALID_BODY), status_code=404)

    sub = db.get(Subscription, record.subscription_id)
    sub_name = sub.name if sub else "未知订阅"

    import html as _h
    body = (
        f"<h2>退订确认</h2>"
        f"<p>你即将退订：<strong>{_h.escape(sub_name)}</strong></p>"
        "<p>确认后，这份订阅会停止推送，所有收件邮箱都不再收到它；你的账号、画像和其它订阅不受影响。</p>"
        f'<form method="post" class="actions" action="/api/v1/unsubscribe/confirm?token={_h.escape(token)}&confirm=1"><button class="btn danger" type="submit">确认退订</button>'
        '<a class="btn" href="/">不退了</a></form>'
    )
    return HTMLResponse(content=_page("退订确认", body))


@router.get("/confirm", response_class=HTMLResponse)
async def legacy_unsubscribe_confirm(token: str, request: Request, db: Session = Depends(get_db)):
    # Old links remain usable, but GET/prefetch never changes a user's subscription.
    return await unsubscribe_page(token, request, db)


@router.post("/confirm", response_class=HTMLResponse)
async def unsubscribe_confirm(
    token: str,
    confirm: str = None,
    db: Session = Depends(get_db),
):
    """Handler"""
    if not confirm:
        return HTMLResponse(content=_page("无效请求", "<h2>无效请求</h2><p>请从邮件底部的「退订」链接进入。</p>"), status_code=400)

    record = db.query(UnsubscribeToken).filter(
        UnsubscribeToken.token == token,
        UnsubscribeToken.is_active == True,
    ).first()

    if not record:
        return HTMLResponse(content=_page("链接已失效", _INVALID_BODY), status_code=404)

# ---
    record.is_active = False
    record.used_at = datetime.utcnow()

    # 真正取消订阅：停用对应的订阅，用户不再收到该订阅的邮件
    sub = db.get(Subscription, record.subscription_id)
    if sub:
        sub.is_active = False
        logger.info(f"退订成功: 订阅 {sub.id} 已停用 (email={record.email})")

    db.commit()

    body = (
        "<h2>已退订</h2>"
        "<p>这份订阅已停止推送，所有收件邮箱都不会再收到它。</p>"
        "<p class=\"muted\">如果是误操作，登录控制台在「订阅管理」里重新打开即可。</p>"
    )
    return HTMLResponse(content=_page("退订成功", body))


_INVALID_BODY = (
    "<h2>退订链接无效或已使用</h2>"
    "<p>这个链接已经用过，或者不完整。如果还在收到这份简报，点最新一封邮件底部的「退订」，"
    "或登录控制台在「订阅管理」里关闭。</p>"
)


def _page(title: str, body: str) -> str:
    from app.utils.compliance import ICP_RECORD, ICP_URL
    return f"""<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0"><title>{title} · 一勺热点 SpoonBrief</title>
<style>
body{{margin:0;font-family:-apple-system,BlinkMacSystemFont,'PingFang SC','Microsoft YaHei',sans-serif;background:#F5F7FB;color:#1F2937;padding:40px 16px}}
.card{{max-width:480px;margin:0 auto;background:#fff;border:1px solid #E6EAF2;border-radius:16px;overflow:hidden}}
.bar{{height:4px;background:#5B7CFF}}.in{{padding:24px}}.brand{{font-size:14px;font-weight:700;color:#5B7CFF}}.brand span{{color:#8A94A6}}
h2{{margin:14px 0 8px;font-size:22px}}p{{color:#4B5563;line-height:1.7;margin:8px 0}}.muted{{color:#8A94A6;font-size:14px}}
.actions{{display:flex;gap:12px;flex-wrap:wrap;margin-top:20px}}.btn{{display:inline-block;padding:11px 22px;border-radius:10px;text-decoration:none;font-weight:600;background:#EEF1F6;color:#374151}}
.btn.danger{{background:#DC2626;color:#fff}}.foot{{max-width:480px;margin:16px auto 0;font-size:12px;color:#9AA3B2;text-align:center;line-height:1.8}}.foot a{{color:#8A94A6}}
</style></head><body><div class="card"><div class="bar"></div><div class="in"><div class="brand">一勺热点 <span>SpoonBrief</span></div>{body}</div></div>
<div class="foot"><a href="/unsubscribe-help">退订说明</a> · <a href="/privacy">隐私政策</a> · <a href="{ICP_URL}" target="_blank" rel="noopener">{ICP_RECORD}</a></div></body></html>"""
