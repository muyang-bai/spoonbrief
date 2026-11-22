"""
信息池：常驻抓取入库 + 简报从池抽取（P2 核心）
"""
from __future__ import annotations
import hashlib
from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime, Text

from app.database import Base


class NewsItem(Base):
    __tablename__ = "news_items"

    id = Column(Integer, primary_key=True, index=True)
    fingerprint = Column(String(64), unique=True, index=True, nullable=False)  # 事件指纹
    source_id = Column(Integer, nullable=True)
    source_name = Column(String(100), nullable=False)
    title = Column(String(500), nullable=False)
    summary = Column(Text, nullable=True)
    link = Column(String(500), nullable=True)
    category = Column(String(20), nullable=True)
    published_at = Column(DateTime, nullable=True)
    credibility = Column(Integer, default=4)
    first_seen_at = Column(DateTime, default=datetime.utcnow)


class NewsEvent(Base):
    __tablename__ = "news_events"

    id = Column(Integer, primary_key=True, index=True)
    fingerprint = Column(String(64), unique=True, index=True, nullable=False)
    title = Column(String(500), nullable=False)
    category = Column(String(20), nullable=True)
    source_count = Column(Integer, default=1)        # 报道此事件的独立来源数
    max_credibility = Column(Integer, default=4)
    source_names = Column(Text, nullable=True)       # JSON 数组字符串
    tokens = Column(Text, nullable=True)             # JSON 数组字符串：语义归并用实体词
    first_seen_at = Column(DateTime, default=datetime.utcnow)
    last_seen_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


def fingerprint_of(title: str) -> str:
    """事件指纹：规范化标题前 15 字（与交叉验证逻辑一致，利于跨源归并同一事件）"""
    import re
    clean = re.sub(r"[^\u4e00-\u9fff\w]", "", title or "")
    return hashlib.md5(clean[:15].lower().encode("utf-8")).hexdigest()
