"""
Authentication routes: send code / register / login / change password
"""

from __future__ import annotations
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import get_db
from app.config import get_settings
from app.models.user import User, UserRole
from app.models.email_address import EmailAddress
from app.models.email_verification import EmailVerificationCode
from app.models.system_config import SystemConfig
from app.schemas.auth import (
    SendCodeRequest, RegisterRequest, LoginRequest,
    TokenResponse, UserInfo,
)
from app.utils.security import hash_password, verify_password, create_access_token
from app.utils.captcha import verify_captcha
from app.deps import get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()


@router.post("/send-code")
async def send_verification_code(req: SendCodeRequest, db: Session = Depends(get_db)):
    # 0. Registration toggle check
    reg_toggle = db.query(SystemConfig).filter(SystemConfig.key == "allow_registration").first()
    if reg_toggle and reg_toggle.value == "false":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "管理员已关闭注册通道")
    
    # 频率限制：同一邮箱60秒内只能请求一次
    sixty_sec_ago = datetime.utcnow() - timedelta(seconds=60)
    existing = (
        db.query(EmailVerificationCode)
        .filter(
            EmailVerificationCode.email == req.email,
            EmailVerificationCode.created_at > sixty_sec_ago,
        )
        .first()
    )
    if existing:
        wait_sec = 60 - int((datetime.utcnow() - existing.created_at).total_seconds())
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            f"请求过于频繁，请在 {wait_sec} 秒后再试"
        )

    # Generate code
    code = EmailVerificationCode.generate_code()
    record = EmailVerificationCode(
        email=req.email,
        code=code,
        purpose="register",
        expires_at=EmailVerificationCode.default_expiry(),
    )
    db.add(record)
    db.commit()

    # Send email via Celery (or console in dev mode)
    from app.tasks.email_tasks import send_verification_email
    from app.utils.task_runner import try_celery_delay
    try_celery_delay(send_verification_email, req.email, code)

    return {"message": "验证码已发送，请查收邮箱（5 分钟内有效）。本地开发模式下请查看后端控制台输出。"}


@router.post("/register", response_model=TokenResponse)
async def register(req: RegisterRequest, db: Session = Depends(get_db)):
    # 0. Registration toggle check
    reg_toggle = db.query(SystemConfig).filter(SystemConfig.key == "allow_registration").first()
    if reg_toggle and reg_toggle.value == "false":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "管理员已关闭注册通道")

    # 1. Verify code
    code_record = (
        db.query(EmailVerificationCode)
        .filter(
            EmailVerificationCode.email == req.email,
            EmailVerificationCode.code == req.code,
            EmailVerificationCode.is_used == False,
            EmailVerificationCode.expires_at > datetime.utcnow(),
        )
        .first()
    )
    if not code_record:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "验证码无效或已过期")

    # 2. Email uniqueness
    if db.query(User).filter(User.email == req.email).first():
        raise HTTPException(status.HTTP_409_CONFLICT, "该邮箱已注册，可直接登录")

    # 3. Nickname uniqueness
    if db.query(User).filter(User.nickname == req.nickname).first():
        raise HTTPException(status.HTTP_409_CONFLICT, "该昵称已被使用，请换一个")

    # 4. Create user
    user = User(
        email=req.email,
        nickname=req.nickname,
        password_hash=hash_password(req.password),
        role=UserRole.USER,
    )
    db.add(user)
    db.flush()

    # 5. Primary email record
    primary_email = EmailAddress(
        user_id=user.id,
        email=req.email,
        is_primary=True,
        is_verified=True,
        verified_at=datetime.utcnow(),
    )
    db.add(primary_email)

    # 6. Mark code as used
    code_record.is_used = True

    db.commit()

    token = create_access_token({"sub": str(user.id), "role": user.role.value})
    return TokenResponse(
        access_token=token,
        user=UserInfo.model_validate(user),
    )


@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest, db: Session = Depends(get_db)):
    # Support email or nickname login
    user = (
        db.query(User)
        .filter((User.email == req.account) | (User.nickname == req.account))
        .first()
    )
    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "账号或密码错误")
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "账号已被禁用")

    user.last_login_at = datetime.utcnow()
    db.commit()

    token = create_access_token({"sub": str(user.id), "role": user.role.value})
    return TokenResponse(
        access_token=token,
        user=UserInfo.model_validate(user),
    )


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str


class SendResetCodeRequest(BaseModel):
    email: str


class ResetPasswordRequest(BaseModel):
    email: str
    code: str
    new_password: str


@router.post("/send-reset-code")
async def send_reset_code(req: SendResetCodeRequest, db: Session = Depends(get_db)):
    """忘记密码：向已注册邮箱发送重置验证码"""
    user = db.query(User).filter(User.email == req.email).first()
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "该邮箱未注册，请先注册")

    # 频率限制：同一邮箱 60 秒内只能请求一次
    sixty_sec_ago = datetime.utcnow() - timedelta(seconds=60)
    existing = (
        db.query(EmailVerificationCode)
        .filter(
            EmailVerificationCode.email == req.email,
            EmailVerificationCode.created_at > sixty_sec_ago,
        )
        .first()
    )
    if existing:
        wait_sec = 60 - int((datetime.utcnow() - existing.created_at).total_seconds())
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, f"请求过于频繁，请在 {wait_sec} 秒后再试")

    code = EmailVerificationCode.generate_code()
    record = EmailVerificationCode(
        email=req.email,
        code=code,
        purpose="reset",
        expires_at=EmailVerificationCode.default_expiry(),
    )
    db.add(record)
    db.commit()

    from app.tasks.email_tasks import send_verification_email
    from app.utils.task_runner import try_celery_delay
    try_celery_delay(send_verification_email, req.email, code)

    return {"message": "重置验证码已发送，请查收邮箱（5 分钟内有效）"}


@router.post("/reset-password")
async def reset_password(req: ResetPasswordRequest, db: Session = Depends(get_db)):
    """忘记密码：验证码校验后重置密码"""
    record = (
        db.query(EmailVerificationCode)
        .filter(
            EmailVerificationCode.email == req.email,
            EmailVerificationCode.code == req.code,
            EmailVerificationCode.purpose == "reset",
            EmailVerificationCode.is_used == False,
            EmailVerificationCode.expires_at > datetime.utcnow(),
        )
        .first()
    )
    if not record:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "验证码无效或已过期")

    user = db.query(User).filter(User.email == req.email).first()
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "该邮箱未注册，请先注册")

    if not User.validate_password(req.new_password):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "新密码不符合规则（至少 8 位，同时包含字母与数字）")

    user.password_hash = hash_password(req.new_password)
    user.force_change_password = False
    record.is_used = True
    db.commit()
    return {"message": "密码已重置，请使用新密码登录"}


@router.put("/change-password")
async def change_password(
    req: ChangePasswordRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not verify_password(req.old_password, user.password_hash):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "原密码错误")
    if not User.validate_password(req.new_password):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "新密码不符合规则（8-72 字节且同时包含字母与数字）")

    user.password_hash = hash_password(req.new_password)
    user.force_change_password = False
    db.commit()
    return {"message": "密码修改成功"}
