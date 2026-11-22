"""
生成的报告（每订阅每次发送一条记录）
"""

from __future__ import annotations
import enum
from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.dialects.mysql import LONGTEXT
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
    user_id = Column(Integer, ForeignKey("hb_users.id"), nullable=False)
    subscription_id = Column(Integer, ForeignKey("subscriptions.id", ondelete="CASCADE"), nullable=False)
# ---
    raw_news_json = Column(Text().with_variant(LONGTEXT(), "mysql"), nullable=True)         # 原始新闻数据
    ai_analysis_html = Column(Text().with_variant(LONGTEXT(), "mysql"), nullable=True)      # AI 分析后 HTML
    decision_json = Column(Text().with_variant(LONGTEXT(), "mysql"), nullable=True)         # 决策层数据（速览/情绪/影响/行动/五维）
    display_json = Column(Text().with_variant(LONGTEXT(), "mysql"), nullable=True)          # 邮件实际展示的条目（含情绪/影响/建议，供网页端复刻邮件版式）
    subject = Column(String(200), nullable=True)        # 邮件主题
# ---
    status = Column(String(20), default=ReportStatus.PENDING.value)
    error_message = Column(Text().with_variant(LONGTEXT(), "mysql"), nullable=True)
# ---
    created_at = Column(DateTime, default=datetime.utcnow)
    sent_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="reports")
    subscription = relationship("Subscription", back_populates="reports")