"""
合规文本（备案号、隐私政策、退订说明）——管理员可编辑
"""

from __future__ import annotations
from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime, Text

from app.database import Base

class ComplianceText(Base):
    __tablename__ = "compliance_texts"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(50), unique=True, nullable=False)
    # 如: icp_record  privacy_policy  unsubscribe_notice
    title = Column(String(100), nullable=False)
    content = Column(Text, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)