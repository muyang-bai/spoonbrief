from __future__ import annotations
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Dict, Any, Union
from datetime import datetime

class UserProfile(BaseModel):
    id: int
    email: str
    nickname: str
    role: str
    persona_json: Optional[str] = None
    last_login_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class UpdatePersonaRequest(BaseModel):
    # —— v1 字段（兼容保留）——
    identities: Optional[List[str]] = None
    student: Optional[dict] = None
    entrepreneur: Optional[dict] = None
    investor: Optional[dict] = None
    creator: Optional[dict] = None
    interests: Optional[Union[List[str], Dict[str, Any]]] = None  # 兼容新旧前端格式
    self_description: Optional[str] = None

    # —— v2 新增：结构化维度（点选为主，均可不填）——
    field: Optional[str] = None                 # 所在领域/专业
    role_title: Optional[str] = None            # 角色/职级
    goals: Optional[List[str]] = None           # 想解决的问题
    domains: Optional[List[str]] = None         # 长期关注赛道
    content_prefs: Optional[List[str]] = None   # 偏好内容类型
    outputs: Optional[List[str]] = None         # 期望简报输出
    avoid: Optional[List[str]] = None           # 规避内容
    perspective: Optional[str] = None           # 决策视角
    horizon: Optional[str] = None               # 时间尺度
    risk: Optional[str] = None                  # 风险偏好
    reading_length: Optional[str] = None        # 阅读习惯
    tone: Optional[str] = None                  # 期望语气
    pain_point: Optional[str] = None            # 最近在纠结的事
    extra_notes: Optional[str] = None           # 任意补充

class EmailAddressCreate(BaseModel):
    email: EmailStr

class EmailAddressOut(BaseModel):
    id: int
    email: str
    is_primary: bool
    is_verified: bool

    class Config:
        from_attributes = True

class ApiKeyCreate(BaseModel):
    provider: str          # deepseek / volcano / openai
    api_key: str
    base_url: Optional[str] = None
    model: Optional[str] = None
    label: Optional[str] = None

class ApiKeyOut(BaseModel):
    id: int
    provider: str
    base_url: Optional[str]
    model: Optional[str]
    label: Optional[str] = None
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True

class UserPromptCreate(BaseModel):
    """用户自建分析模板"""
    name: str
    description: Optional[str] = None
    system_prompt: str
    user_prompt_template: str = ""
    model: str = "deepseek-v4-flash"
    temperature: int = 70
    max_tokens: int = 1500
    is_open_source: bool = False
    suitable_for: Optional[str] = None
    tags: Optional[str] = None
    usage_hint: Optional[str] = None

class UserPromptUpdate(BaseModel):
    """用户模板更新（全部可选）"""
    name: Optional[str] = None
    description: Optional[str] = None
    system_prompt: Optional[str] = None
    user_prompt_template: Optional[str] = None
    model: Optional[str] = None
    temperature: Optional[int] = None
    max_tokens: Optional[int] = None
    is_open_source: Optional[bool] = None
    suitable_for: Optional[str] = None
    tags: Optional[str] = None
    usage_hint: Optional[str] = None

class SkillImportRequest(BaseModel):
    """导入 Skill JSON（前端字段名 schema，映射到 schema_version 避免遮蔽基类属性）"""
    schema_version: str = Field(default="hotmail-skill-v1", alias="schema")
    name: str
    description: Optional[str] = None
    system_prompt: str
    user_prompt_template: str = ""
    model: str = "deepseek-v4-flash"
    temperature: int = 70
    max_tokens: int = 1500
    suitable_for: Optional[str] = None
    tags: Optional[str] = None
    usage_hint: Optional[str] = None