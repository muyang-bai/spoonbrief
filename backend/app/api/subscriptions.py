"""
订阅管理路由
"""

from __future__ import annotations
import asyncio
import concurrent.futures
from typing import List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from loguru import logger

from app.database import get_db
from app.deps import get_current_user, check_api_quota
from app.models.user import User
from app.models.subscription import Subscription
from app.schemas.subscription import SubscriptionCreate, SubscriptionUpdate, SubscriptionOut

router = APIRouter(prefix="/subscriptions", tags=["订阅"])


@router.get("/", response_model=List[SubscriptionOut])
async def list_subscriptions(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    subs = db.query(Subscription).filter(Subscription.user_id == user.id).all()
    return subs


@router.post("/", response_model=SubscriptionOut, status_code=201)
async def create_subscription(
    req: SubscriptionCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    count = db.query(Subscription).filter(Subscription.user_id == user.id).count()
    if count >= 3:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "最多只能创建3个订阅，请删除现有订阅后再添加")

    # 校验 cron 表达式（无效直接拒绝，避免静默回退默认时间）
    from croniter import croniter
    from dateutil import tz as _tz
    try:
        croniter(req.cron_expr, datetime.now(tz=_tz.gettz(req.timezone or "Asia/Shanghai"))).get_next(datetime)
    except Exception:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "发送时间格式无效，请重新设置")

    sub = Subscription(
        user_id=user.id,
        **req.model_dump(),
    )
    db.add(sub)
    db.commit()
    db.refresh(sub)

    from app.tasks.report_tasks import _update_next_sent
    _update_next_sent(db, sub.id)

    return sub


@router.put("/{sub_id}", response_model=SubscriptionOut)
async def update_subscription(
    sub_id: int,
    req: SubscriptionUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    sub = db.query(Subscription).filter(
        Subscription.id == sub_id,
        Subscription.user_id == user.id,
    ).first()
    if not sub:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "订阅不存在")

    for k, v in req.model_dump(exclude_unset=True).items():
        setattr(sub, k, v)

    # 校验 cron 表达式（若本次更新了 cron）
    if req.cron_expr is not None:
        from croniter import croniter
        from dateutil import tz as _tz
        try:
            croniter(sub.cron_expr, datetime.now(tz=_tz.gettz(sub.timezone or "Asia/Shanghai"))).get_next(datetime)
        except Exception:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "发送时间格式无效，请重新设置")

    db.commit()
    db.refresh(sub)

    from app.tasks.report_tasks import _update_next_sent
    _update_next_sent(db, sub.id)

    return sub


@router.delete("/{sub_id}")
async def delete_subscription(sub_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    sub = db.query(Subscription).filter(
        Subscription.id == sub_id,
        Subscription.user_id == user.id,
    ).first()
    if not sub:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "订阅不存在，请刷新页面后重试")
    db.delete(sub)
    db.commit()
    return {"message": "订阅已删除"}


@router.post("/{sub_id}/trigger")
async def trigger_now(sub_id: int, user: User = Depends(check_api_quota), db: Session = Depends(get_db)):
    """立即发送：同步执行报告生成并等待完成（与调度器共享防重锁）"""
    sub = db.query(Subscription).filter(
        Subscription.id == sub_id,
        Subscription.user_id == user.id,
    ).first()
    if not sub:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "订阅不存在，请先创建订阅")

    # 与调度器共用同一把防重锁：防止手动触发与定时触发并发导致重复发送
    from app.services.local_scheduler import _running_subscriptions
    if sub_id in _running_subscriptions:
        raise HTTPException(status.HTTP_409_CONFLICT, "该订阅正在生成中，请稍候片刻")
    _running_subscriptions.add(sub_id)

    try:
        from app.tasks.report_tasks import generate_report

        # Run synchronously in a thread pool, wait for completion
        loop = asyncio.get_event_loop()
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            result = await loop.run_in_executor(pool, generate_report.run, sub_id)

        # Check the generated report status
        from app.models.report import Report
        latest = db.query(Report).filter(
            Report.subscription_id == sub_id
        ).order_by(Report.created_at.desc()).first()

        if latest:
            if latest.status == "sent":
                # 扣费已统一在 generate_report 内完成（手动/定时同规则），此处不再重复扣
                return {
                    "message": "简报已推送，请查收邮箱",
                    "report_id": latest.id,
                    "status": "sent",
                    "subject": latest.subject,
                }
            elif latest.status == "failed":
                return {
                    "message": f"报告生成失败: {latest.error_message or '未知错误'}",
                    "report_id": latest.id,
                    "status": "failed",
                    "error": latest.error_message,
                }
            else:
                return {
                    "message": "报告已生成",
                    "report_id": latest.id,
                    "status": latest.status,
                }
        else:
            return {"message": "报告生成任务已完成，请在历史报告中查看"}
    finally:
        _running_subscriptions.discard(sub_id)