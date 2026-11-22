"""AI token 用量明细（后台用量看板数据源）"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, DateTime, Float, Integer, String

from app.database import Base


class TokenUsage(Base):
    __tablename__ = "token_usage"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True, nullable=True)
    subscription_id = Column(Integer, nullable=True)
    report_id = Column(Integer, index=True, nullable=True)
    model = Column(String(64), nullable=True)
    stage = Column(String(32), nullable=True)          # analyze / decision / test
    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    cost_yuan = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
