"""简报反馈（邮件底部一键「有用 / 没用」）

用途：邮件里直接收集读后反馈，回流用于个性化推荐与内容质量迭代（数据飞轮）。
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String

from app.database import Base


class ReportFeedback(Base):
    __tablename__ = "report_feedback"

    id = Column(Integer, primary_key=True, index=True)
    report_id = Column(Integer, index=True, nullable=False)
    user_id = Column(Integer, index=True, nullable=True)
    subscription_id = Column(Integer, nullable=True)
    value = Column(String(8), nullable=False)  # up / down
    reason = Column(String(32), nullable=True)  # direction/shallow/stale/evidence/length
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
