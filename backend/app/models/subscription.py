"""
用户订阅项（最多 3 个/用户）
"""

from __future__ import annotations
import enum
from datetime import datetime

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship

from app.database import Base

class TimeWindow(str, enum.Enum):
    TODAY = "today"
    D3 = "3d"
    D7 = "7d"
    D10 = "10d"
    D15 = "15d"
    D20 = "20d"
    D25 = "25d"
    D30 = "30d"

    @property
    def days(self) -> int:
        mapping = {
            "today": 1, "3d": 3, "7d": 7, "10d": 10,
            "15d": 15, "20d": 20, "25d": 25, "30d": 30,
        }
        return mapping[self.value]

class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
# ---
    name = Column(String(100), nullable=False)
    # 信息类别（系统预置 ID 或 "custom"）
    category_id = Column(String(50), nullable=True)
# ---
    keywords = Column(Text, nullable=True)   # "半导体,国产替代"
# ---
    time_window = Column(String(10), default="7d", nullable=False)
    # 定时（cron 表达式 + 时区）
    cron_expr = Column(String(100), default="0 9 * * *", nullable=False)
    timezone = Column(String(50), default="Asia/Shanghai", nullable=False)
    # 上次/下次发送时间
    last_sent_at = Column(DateTime, nullable=True)
    next_sent_at = Column(DateTime, nullable=True)
    # AI 分析开关
    ai_analysis = Column(Boolean, default=True, nullable=False)
    # 使用自定义 API
    use_custom_api = Column(Boolean, default=False, nullable=False)
    # 绑定 Prompt 模板
    prompt_template_id = Column(Integer, ForeignKey("prompt_templates.id"), nullable=True)
    # 绑定 API Key（NULL=平台兜底）
    api_key_id = Column(Integer, ForeignKey("api_keys.id"), nullable=True)
    # 订阅级月度推送上限（NULL=不限；超出自动跳过并通知，防"忘记关闭白白消耗"）
    monthly_quota = Column(Integer, nullable=True)
# ---
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# ---
    user = relationship("User", back_populates="subscriptions")
    prompt_template = relationship("PromptTemplate")
    # passive_deletes=True：删除订阅时由数据库 FK ON DELETE CASCADE 清理 reports，
    # 禁止 ORM 先置空 subscription_id（NOT NULL 列，曾导致删除订阅 500）
    reports = relationship("Report", back_populates="subscription", passive_deletes=True)