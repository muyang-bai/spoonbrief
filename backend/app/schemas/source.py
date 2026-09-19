from __future__ import annotations
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class NewsSourceCreate(BaseModel):
    name: str
    source_type: str
    source_category: str = "综合"
    url: str
    api_key_ref: Optional[str] = None
    fetch_interval: int = 30
    credibility: int = 5
    description: Optional[str] = None


class NewsSourceUpdate(BaseModel):
    name: Optional[str] = None
    source_category: Optional[str] = None
    url: Optional[str] = None
    api_key_ref: Optional[str] = None
    fetch_interval: Optional[int] = None
    credibility: Optional[int] = None
    is_active: Optional[bool] = None
    description: Optional[str] = None


class NewsSourceOut(NewsSourceCreate):
    id: int
    is_active: bool
    api_remaining: int = -1
    last_fetch_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True