"""
用户收件邮箱管理
"""

from __future__ import annotations
from typing import List
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models.user import User
from app.models.email_address import EmailAddress
from app.models.email_verification import EmailVerificationCode
from app.schemas.user import EmailAddressCreate, EmailAddressOut

from app.services.recipients import list_effective_emails, verification_target, normalize_email

router = APIRouter(prefix="/emails", tags=["收件邮箱"])

@router.get("/", response_model=List[EmailAddressOut])
async def list_emails(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return list_effective_emails(db,user)

@router.post("/", response_model=EmailAddressOut, status_code=201)
async def add_email(req: EmailAddressCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    count = len(list_effective_emails(db,user))
    if count >= 3:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "最多只能添加3个收件邮箱，请删除不需要的邮箱后再添加")

    existing = db.query(EmailAddress).filter(EmailAddress.user_id == user.id).all()
    if normalize_email(req.email) == normalize_email(user.email) or any(normalize_email(e.email) == normalize_email(req.email) for e in existing):
        raise HTTPException(status.HTTP_409_CONFLICT, "该邮箱已被添加，请勿重复添加")

    email = EmailAddress(user_id=user.id, email=req.email, is_primary=False, is_verified=False)
    db.add(email)
    db.commit()
    db.refresh(email)
    return email

@router.post("/{email_id}/send-verify")
async def send_verify_code(email_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    email = verification_target(db,user,email_id)
    if not email:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "收件邮箱不存在，请刷新页面后重试")
    if email.is_verified:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "该邮箱已验证通过，无需重复验证")

    # 频率限制：同一邮箱60秒内只能请求一次
    sixty_sec_ago = datetime.utcnow() - timedelta(seconds=60)
    existing_code = (
        db.query(EmailVerificationCode)
        .filter(
            EmailVerificationCode.email == email.email,
            EmailVerificationCode.created_at > sixty_sec_ago,
        )
        .first()
    )
    if existing_code:
        wait_sec = 60 - int((datetime.utcnow() - existing_code.created_at).total_seconds())
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            f"请求过于频繁，请在 {wait_sec} 秒后再试"
        )

    code = EmailVerificationCode.generate_code()
    record = EmailVerificationCode(
        email=email.email,
        code=code,
        purpose="email_verify",
        expires_at=EmailVerificationCode.default_expiry(),
    )
    db.add(record)
    db.commit()

    from app.tasks.email_tasks import send_verification_email
    from app.utils.task_runner import try_celery_delay
    try_celery_delay(send_verification_email, email.email, code, "验证收件邮箱")
    return {"message": "验证码已提交发送，请查收；未收到请稍后重试"}

@router.post("/{email_id}/verify")
async def verify_email(email_id: int, code: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    email = verification_target(db,user,email_id)
    if not email:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "收件邮箱不存在")

    record = db.query(EmailVerificationCode).filter(
        EmailVerificationCode.email == email.email,
        EmailVerificationCode.code == code,
        EmailVerificationCode.purpose == "email_verify",
        EmailVerificationCode.is_used == False,
        EmailVerificationCode.expires_at > datetime.utcnow(),
    ).first()
    if not record:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "验证码无效或已过期，请重新发送")

    if email_id == 0:
        # Only a successfully verified, explicit user action may create this row.
        email = db.query(EmailAddress).filter(EmailAddress.user_id == user.id,
                                              EmailAddress.email == user.email).first()
        if email is None:
            email = EmailAddress(user_id=user.id,email=user.email,is_primary=True,is_verified=False)
            db.add(email)
    email.is_verified = True
    email.verified_at = datetime.utcnow()
    record.is_used = True
    db.commit()
    return {"message": "邮箱验证成功"}

@router.delete("/{email_id}")
async def delete_email(email_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    email = db.query(EmailAddress).filter(
        EmailAddress.id == email_id,
        EmailAddress.user_id == user.id,
    ).first()
    if not email:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "收件邮箱不存在，可能已被删除")
    if email.is_primary or normalize_email(email.email) == normalize_email(user.email):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "主邮箱不可删除（注册邮箱作为账号标识，无法移除）")
    db.delete(email)
    db.commit()
    return {"message": "收件邮箱已删除"}
