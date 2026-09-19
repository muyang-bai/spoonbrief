"""
信息源（RSS / API），管理员可增删
"""

from __future__ import annotations
import enum
from datetime import datetime

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum, Text, Float

from app.database import Base

class SourceType(str, enum.Enum):
    RSS = "rss"
    DAILYHOT = "dailyhot"
    NEWSAPI = "newsapi"
    BING_NEWS = "bing_news"

class SourceCategory(str, enum.Enum):
    COMPREHENSIVE = "综合"
    TECH = "科技"
    FINANCE = "财经"
    INTERNATIONAL = "国际"
    POLITICS = "时政"
    SOCIETY = "社会"
    ENTERTAINMENT = "娱乐"
    SPORTS = "体育"
    CUSTOM = "自定义"

class NewsSource(Base):
    __tablename__ = "news_sources"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    source_type = Column(Enum(SourceType), nullable=False)
    source_category = Column(Enum(SourceCategory), default=SourceCategory.COMPREHENSIVE)
    url = Column(String(500), nullable=False)
    api_key_ref = Column(String(50), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    fetch_interval = Column(Integer, default=30)
    last_fetch_at = Column(DateTime, nullable=True)
    # 可信度权重（1-10，官方媒体=10，自媒体=2）
    credibility = Column(Integer, default=5, nullable=False)
    # API 剩余调用次数（-1 表示无限制，RSS 源使用 -1）
    api_remaining = Column(Integer, default=-1)
    # 上次剩余调用次数更新时间
    api_remaining_updated = Column(DateTime, nullable=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)