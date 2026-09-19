from __future__ import annotations
from pydantic import BaseModel, field_validator
from typing import Optional, List
from datetime import datetime, timezone

class SubscriptionCreate(BaseModel):
    name: str
    category_id: Optional[str] = None
    keywords: Optional[str] = None
    time_window: str = "7d"
    cron_expr: str = "0 9 * * *"
    timezone: str = "Asia/Shanghai"
    ai_analysis: bool = True
    use_custom_api: bool = False
    prompt_template_id: Optional[int] = None
    api_key_id: Optional[int] = None
    monthly_quota: Optional[int] = None

    @field_validator("time_window")
    @classmethod
    def check_window(cls, v):
        allowed = {"today", "3d", "7d", "10d", "15d", "20d", "25d", "30d"}
        if v not in allowed:
            raise ValueError(f"time_window must be one of {allowed}")
        return v

class SubscriptionUpdate(BaseModel):
    name: Optional[str] = None
    category_id: Optional[str] = None
    keywords: Optional[str] = None
    time_window: Optional[str] = None
    cron_expr: Optional[str] = None
    timezone: Optional[str] = None
    ai_analysis: Optional[bool] = None
    use_custom_api: Optional[bool] = None
    prompt_template_id: Optional[int] = None
    api_key_id: Optional[int] = None
    is_active: Optional[bool] = None
    monthly_quota: Optional[int] = None

class SubscriptionOut(BaseModel):
    id: int
    user_id: int
    name: str
    category_id: Optional[str]
    keywords: Optional[str]
    time_window: str
    cron_expr: str
    timezone: str
    ai_analysis: bool
    use_custom_api: bool
    prompt_template_id: Optional[int]
    api_key_id: Optional[int]
    is_active: bool
    monthly_quota: Optional[int]
    last_sent_at: Optional[datetime]
    next_sent_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True

    @field_validator("last_sent_at", "next_sent_at", "created_at", mode="before")
    @classmethod
    def make_tz_aware(cls, v):
        if v is not None and v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v