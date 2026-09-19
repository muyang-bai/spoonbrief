"""
生成的报告（每订阅每次发送一条记录）
"""

from __future__ import annotations
import enum
from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship

from app.database import Base

class ReportStatus(str, enum.Enum):
    PENDING = "pending"
    FETCHING = "fetching"
    ANALYZING = "analyzing"
    SENT = "sent"
    FAILED = "failed"

class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    subscription_id = Column(Integer, ForeignKey("subscriptions.id", ondelete="CASCADE"), nullable=False)
# ---
    raw_news_json = Column(Text, nullable=True)         # 原始新闻数据
    ai_analysis_html = Column(Text, nullable=True)      # AI 分析后 HTML
    subject = Column(String(200), nullable=True)        # 邮件主题
# ---
    status = Column(String(20), default=ReportStatus.PENDING.value)
    error_message = Column(Text, nullable=True)
# ---
    created_at = Column(DateTime, default=datetime.utcnow)
    sent_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="reports")
    subscription = relationship("Subscription", back_populates="reports")