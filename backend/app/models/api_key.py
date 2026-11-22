"""
用户自有 API Key（加密存储），管理员可建平台 Key 池
"""

from __future__ import annotations
from datetime import datetime

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from app.database import Base

class ApiKey(Base):
    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("hb_users.id", ondelete="CASCADE"), nullable=False)
    provider = Column(String(50), nullable=False)
    encrypted_key = Column(String(500), nullable=False)
    base_url = Column(String(300), nullable=True)
    model = Column(String(100), nullable=True)
    label = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True)
    is_platform = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="api_keys")