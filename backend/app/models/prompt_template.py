"""
AI Prompt 模板库 — Skill 化版本
"""

from __future__ import annotations
from datetime import datetime

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey

from app.database import Base


class PromptTemplate(Base):
    __tablename__ = "prompt_templates"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    # 模板简介（面向用户的一两句话说明）
    description = Column(Text, nullable=True)
    # 角色设定提示词
    system_prompt = Column(Text, nullable=False)
    # 分析指令模板（支持 {content} {persona} 变量）
    user_prompt_template = Column(Text, nullable=False)
    # 模型选择（默认跟随平台）
    model = Column(String(100), default="deepseek-v4-flash")
    # 温度（0-100，使用时除以100；0=严谨 100=发散）
    temperature = Column(Integer, default=70)
    # 最大输出 token 数
    max_tokens = Column(Integer, default=1500)

    is_default = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    # 平台模板（管理员创建，用户只可选不可查看详情）
    is_platform = Column(Boolean, default=False)
    # 开源模板（用户创建并勾选开源，所有用户可见可用）
    is_open_source = Column(Boolean, default=False)
    # 适用画像（逗号分隔: student,entrepreneur,investor,creator）
    suitable_for = Column(String(200), nullable=True)
    # 标签（逗号分隔: 教育,考研,AI）
    tags = Column(String(200), nullable=True)
    # 使用提示（显示给用户的简短说明）
    usage_hint = Column(String(500), nullable=True)

    # 创建者（NULL=平台模板）
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
