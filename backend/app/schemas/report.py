from __future__ import annotations
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class ReportOut(BaseModel):
    id: int
    user_id: int
    subscription_id: int
    subject: Optional[str]
    status: str
    error_message: Optional[str]
    created_at: datetime
    sent_at: Optional[datetime]
    ai_analysis_html: Optional[str] = None

    class Config:
        from_attributes = True