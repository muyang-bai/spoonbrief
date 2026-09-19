"""
FastAPI 依赖注入
"""

from __future__ import annotations
from datetime import datetime
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User, UserRole
from app.utils.security import decode_access_token

security_scheme = HTTPBearer(auto_error=False)

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
    db: Session = Depends(get_db),
) -> User:
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未提供认证信息",
        )
    payload = decode_access_token(credentials.credentials)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="认证已过期，请重新登录",
        )
    try:
        user_id = int(payload.get("sub"))
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="认证信息无效",
        )
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不存在")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="账号已被禁用")
    return user

async def get_admin_user(user: User = Depends(get_current_user)) -> User:
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="需要管理员权限")
    return user

def _monthly_reset(user: User) -> bool:
    """按月自动重置配额；返回是否发生重置"""
    now = datetime.utcnow()
    if user.api_quota_reset_at is None or now >= user.api_quota_reset_at:
        user.api_quota_used = 0
        # 下月1号 00:00 UTC
        if now.month == 12:
            next_month = datetime(now.year + 1, 1, 1)
        else:
            next_month = datetime(now.year, now.month + 1, 1)
        user.api_quota_reset_at = next_month
        return True
    return False


def ensure_quota_available(user: User, db: Session) -> bool:
    """额度校验（API 与定时任务共用）：按月重置 + 判断是否还有额度"""
    if _monthly_reset(user):
        db.commit()
    return user.api_quota_used < user.api_quota_total


async def check_api_quota(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> User:
    """检查API配额（仅校验+按月自动重置，不扣费；成功后再扣费）"""
    if not ensure_quota_available(user, db):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="本月额度已用完，请等待下月重置或联系管理员",
        )
    return user


def consume_api_quota(user: User, db: Session) -> None:
    """报告生成成功后扣减一次配额"""
    user.api_quota_used += 1
    db.commit()