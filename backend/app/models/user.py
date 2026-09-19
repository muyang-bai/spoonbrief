"""
用户模型
"""

from __future__ import annotations
import enum
import re
from datetime import datetime

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum
from sqlalchemy.orm import relationship

from app.database import Base

class UserRole(str, enum.Enum):
    USER = "user"
    ADMIN = "admin"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    nickname = Column(String(50), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), default=UserRole.USER, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    force_change_password = Column(Boolean, default=False, nullable=False)
    api_quota_total = Column(Integer, default=60, nullable=False)
    api_quota_used = Column(Integer, default=0, nullable=False)
    api_quota_reset_at = Column(DateTime, nullable=True)
    # 用户画像（JSON 字符串）
    persona_json = Column(String(2000), nullable=True)
# ---
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login_at = Column(DateTime, nullable=True)

# ---
    email_addresses = relationship("EmailAddress", back_populates="user", cascade="all, delete-orphan")
    subscriptions = relationship("Subscription", back_populates="user", cascade="all, delete-orphan")
    api_keys = relationship("ApiKey", back_populates="user", cascade="all, delete-orphan")
    reports = relationship("Report", back_populates="user", cascade="all, delete-orphan")

    # ── 昵称校验：字母 / 连字符 / 中文 ──
    @staticmethod
    def validate_nickname(nickname: str) -> bool:
        """
        昵称规则：2-20 位，只允许字母、连字符、中文
        """
        if not (2 <= len(nickname) <= 20):
            return False
        pattern = r'^[a-zA-Z\u4e00-\u9fff\-]+$'
        return bool(re.match(pattern, nickname))

    @staticmethod
    def validate_password(password: str) -> bool:
        """
        密码规则：8-72 字节且同时包含字母与数字（bcrypt 上限 72 字节）
        """
        if len(password.encode("utf-8")) > 72:
            return False
        if len(password) < 8:
            return False
        has_alpha = any(c.isalpha() for c in password)
        has_digit = any(c.isdigit() for c in password)
        return has_alpha and has_digit