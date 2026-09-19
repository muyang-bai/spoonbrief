"""
关键词搜索统计（管理员数据面板用）
"""

from __future__ import annotations
from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime, Index

from app.database import Base

class KeywordStat(Base):
    __tablename__ = "keyword_stats"

    id = Column(Integer, primary_key=True, index=True)
    keyword = Column(String(100), nullable=False, index=True)
    search_count = Column(Integer, default=1)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("idx_keyword", "keyword"),
    )