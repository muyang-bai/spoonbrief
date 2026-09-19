"""
退订路由（无需登录，通过 token 退订）
"""

from __future__ import annotations
from datetime import datetime

from fastapi import APIRouter, HTTPException, status, Request, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from loguru import logger

from app.database import get_db
from app.models.unsubscribe_token import UnsubscribeToken
from app.models.subscription import Subscription
from app.models.email_address import EmailAddress

router = APIRouter(prefix="/unsubscribe", tags=["admin"])

@router.get("", response_class=HTMLResponse)
async def unsubscribe_page(token: str, request: Request, db: Session = Depends(get_db)):
    """Handler"""
    record = db.query(UnsubscribeToken).filter(
        UnsubscribeToken.token == token,
        UnsubscribeToken.is_active == True,
    ).first()

    if not record:
        return HTMLResponse(content="<h2>退订链接无效或已使用</h2>", status_code=404)

    sub = db.get(Subscription, record.subscription_id)
    sub_name = sub.name if sub else "未知订阅"

    return HTMLResponse(content=f"""
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="utf-8">
      <meta name="viewport" content="width=device-width, initial-scale=1.0">
      <title>退订确认 - 一勺热点</title>
      <style>
        body {{ font-family: sans-serif; background: #f4f5f7; padding: 40px; text-align: center; }}
        .card {{ max-width: 480px; margin: 0 auto; background: #fff; border-radius: 12px; padding: 40px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
        .btn {{ display: inline-block; padding: 12px 32px; border-radius: 8px; text-decoration: none; font-weight: bold; margin: 0 8px; }}
        .btn-danger {{ background: #ef4444; color: #fff; }}
        .btn-cancel {{ background: #e5e7eb; color: #374151; }}
      </style>
    </head>
    <body>
      <div class="card">
        <h2 style="color: #4c1d95;">退订确认</h2>
        <p style="color: #6b7280; margin: 16px 0;">
          你即将取消订阅：<strong>{sub_name}</strong><br>
          退订后，此邮箱将不再收到该订阅的热点情报邮件。
        </p>
        <div style="margin-top: 24px; display: flex; gap: 12px; justify-content: center; flex-wrap: wrap;">
          <a href="/api/v1/unsubscribe/confirm?token={token}&confirm=1"
             class="btn btn-danger"
             style="display:inline-block; min-width:150px; padding:12px 24px; border-radius:8px; text-align:center; text-decoration:none; font-weight:bold; background:#ef4444; color:#fff;">确认退订</a>
          <a href="/"
             class="btn btn-cancel"
             style="display:inline-block; min-width:150px; padding:12px 24px; border-radius:8px; text-align:center; text-decoration:none; font-weight:bold; background:#e5e7eb; color:#374151;">不退了</a>
        </div>
      </div>
    </body>
    </html>
    """)

@router.get("/confirm", response_class=HTMLResponse)
async def unsubscribe_confirm(
    token: str,
    confirm: str = None,
    db: Session = Depends(get_db),
):
    """Handler"""
    if not confirm:
        return HTMLResponse(content="<h2>无效请求</h2>", status_code=400)

    record = db.query(UnsubscribeToken).filter(
        UnsubscribeToken.token == token,
        UnsubscribeToken.is_active == True,
    ).first()

    if not record:
        return HTMLResponse(content="<h2>退订链接无效或已使用</h2>", status_code=404)

# ---
    record.is_active = False
    record.used_at = datetime.utcnow()

    # 真正取消订阅：停用对应的订阅，用户不再收到该订阅的邮件
    sub = db.get(Subscription, record.subscription_id)
    if sub:
        sub.is_active = False
        logger.info(f"退订成功: 订阅 {sub.id} 已停用 (email={record.email})")

    db.commit()

    return HTMLResponse(content="""
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="utf-8">
      <meta name="viewport" content="width=device-width, initial-scale=1.0">
      <title>退订成功 - 一勺热点</title>
      <style>
        body { font-family: sans-serif; background: #f4f5f7; padding: 40px; text-align: center; }
        .card { max-width: 480px; margin: 0 auto; background: #fff; border-radius: 12px; padding: 40px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
      </style>
    </head>
    <body>
      <div class="card">
        <div style="font-size: 48px;">✅</div>
        <h2 style="color: #4c1d95;">退订成功</h2>
        <p style="color: #6b7280;">你已成功取消订阅，此邮箱将不再收到该订阅的热点情报邮件。</p>
        <p style="color: #9ca3af; font-size: 12px; margin-top: 24px;">
          如果是误操作，可登录控制台重新启用订阅。
        </p>
      </div>
    </body>
    </html>
    """)
