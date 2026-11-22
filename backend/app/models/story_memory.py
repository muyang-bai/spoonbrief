"""订阅级事件记忆（t162）：跨期去重与事件进展追踪。

一条记录 = 一个"事件"（同事件的转载/换标题合并后只留一条），
保留首次出现、最近推送、已用来源与已知事实，供下一次生成比较"新增了什么"。
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, Column, DateTime, Integer, String, Text
from sqlalchemy.dialects.mysql import LONGTEXT

from app.database import Base


class StoryMemory(Base):
    __tablename__ = "hb_story_memory"

    id = Column(Integer, primary_key=True, index=True)
    subscription_id = Column(Integer, index=True, nullable=False)
    event_key = Column(String(64), index=True, nullable=False)
    title = Column(String(300), nullable=True)
    keywords = Column(String(300), nullable=True)
    first_seen_at = Column(DateTime, default=datetime.utcnow)
    last_seen_at = Column(DateTime, default=datetime.utcnow)
    last_pushed_at = Column(DateTime, nullable=True)
    last_report_id = Column(Integer, nullable=True)
    push_count = Column(Integer, default=0)
    sources_json = Column(Text().with_variant(LONGTEXT(), "mysql"), nullable=True)
    facts_json = Column(Text().with_variant(LONGTEXT(), "mysql"), nullable=True)
    status = Column(String(16), default="active")
    # t180：实体链接与 SimHash（同事件换标题也能匹配）
    entities_json = Column(Text().with_variant(LONGTEXT(), "mysql"), nullable=True)
    simhash = Column(BigInteger, default=0)
    action = Column(String(16), nullable=True)
