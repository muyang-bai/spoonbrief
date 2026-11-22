from __future__ import annotations
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class AdminUserOut(BaseModel):
    id: int
    email: str
    nickname: str
    role: str
    is_active: bool
    created_at: datetime
    last_login_at: Optional[datetime]
    subscription_count: int = 0
    api_quota_total: int = 60
    api_quota_used: int = 0
    api_quota_reset_at: Optional[datetime] = None
    permission: str = "member"
    member_tier: Optional[str] = None
    member_tier_label: str = "未同步"
    class Config:
        from_attributes = True

class AdminUserUpdate(BaseModel):
    nickname: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None

class SmtpConfig(BaseModel):
    host: str
    port: int
    user: str
    password: str
    from_email: str
    from_name: str
    use_ssl: bool = True

class AiConfig(BaseModel):
    provider: str = "deepseek"
    api_key: str
    base_url: str
    model: str
    enabled: bool = True

class AnnouncementCreate(BaseModel):
    title: str
    body: str
    is_pinned: bool = False

class AnnouncementOut(AnnouncementCreate):
    id: int
    published_at: datetime
    erased_at: Optional[datetime]
    class Config:
        from_attributes = True

class ComplianceTextUpdate(BaseModel):
    key: str
    content: str

class ComplianceTextOut(BaseModel):
    key: str
    title: str
    content: str
    updated_at: datetime
    class Config:
        from_attributes = True

class PromptTemplateCreate(BaseModel):
    name: str
    description: Optional[str] = None
    system_prompt: str
    user_prompt_template: str
    model: str = "deepseek-v4-flash"
    temperature: int = 70
    max_tokens: int = 1500
    is_default: bool = False
    is_platform: bool = False
    is_open_source: bool = False
    suitable_for: Optional[str] = None
    tags: Optional[str] = None
    usage_hint: Optional[str] = None

class PromptTemplateOut(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    system_prompt: str = ""
    user_prompt_template: str = ""
    model: str = "deepseek-v4-flash"
    temperature: int = 70
    max_tokens: int = 1500
    is_default: bool = False
    is_active: bool = True
    is_platform: bool = False
    is_open_source: bool = False
    suitable_for: Optional[str] = None
    tags: Optional[str] = None
    usage_hint: Optional[str] = None
    owner_id: Optional[int] = None
    created_at: Optional[datetime] = None
    class Config:
        from_attributes = True

class DashboardStats(BaseModel):
    total_users: int
    active_users: int
    total_subscriptions: int
    total_reports_sent: int
    total_emails_sent: int
    total_reports: int = 0
    today_reports: int = 0
    active_subscriptions: int = 0
    keyword_top20: List[dict]
    category_distribution: List[dict]
    user_growth: List[dict]
    email_delivery_rate: float
    linked_users: int = 0
    reports_24h: int = 0
    failed_24h: int = 0
    tokens_24h: int = 0
    cost_yuan_24h: float = 0.0
    token_model_24h: Optional[str] = None
    subscription_topics: List[dict] = []

