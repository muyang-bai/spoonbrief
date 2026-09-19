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
    identities: Optional[List[str]] = None
    student: Optional[dict] = None
    entrepreneur: Optional[dict] = None
    investor: Optional[dict] = None
    creator: Optional[dict] = None
    interests: Optional[Union[List[str], Dict[str, Any]]] = None  # 兼容新旧前端格式
    self_description: Optional[str] = None

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