"""
管理员公告（可发布/擦除）
"""

from __future__ import annotations
from datetime import datetime

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text

from app.database import Base

class Announcement(Base):
    __tablename__ = "announcements"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    body = Column(Text, nullable=False)
    # 发布 / 擦除时间
    published_at = Column(DateTime, default=datetime.utcnow)
    erased_at = Column(DateTime, nullable=True)       # 非空 = 已擦除（不展示）
    is_pinned = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)