"""
邮箱验证码（注册 + 备用邮箱验证）
"""

from __future__ import annotations
from datetime import datetime, timedelta

from sqlalchemy import Column, Integer, String, DateTime, Boolean

from app.database import Base

class EmailVerificationCode(Base):
    __tablename__ = "email_verification_codes"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), nullable=False, index=True)
    code = Column(String(6), nullable=False)
    purpose = Column(String(20), default="register")  # register / email_verify
    is_used = Column(Boolean, default=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    @staticmethod
    def generate_code() -> str:
        import secrets
        return str(100000 + secrets.randbelow(900000))

    @staticmethod
    def default_expiry() -> datetime:
        return datetime.utcnow() + timedelta(minutes=5)