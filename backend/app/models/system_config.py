"""
系统级配置（管理员后台可改，无需重启）
"""

from __future__ import annotations
from datetime import datetime

from sqlalchemy import Column, Integer, String, Boolean, DateTime

from app.database import Base

class SystemConfig(Base):
    __tablename__ = "system_config"

    id = Column(Integer, primary_key=True)
    key = Column(String(100), unique=True, nullable=False, index=True)
    value = Column(String(1000), nullable=True)
    value_type = Column(String(20), default="string")    # string/int/bool/json
    description = Column(String(500), nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)