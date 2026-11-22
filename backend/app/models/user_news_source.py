"""
用户自定义 RSS 信息源（个人源池，仅用于该用户的简报）
"""
from __future__ import annotations
from datetime import datetime

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text

from app.database import Base


class UserNewsSource(Base):
    __tablename__ = "user_news_sources"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("hb_users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    url = Column(String(500), nullable=False)
    category = Column(String(50), default="自定义", nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    last_fetch_at = Column(DateTime, nullable=True)
    last_error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
