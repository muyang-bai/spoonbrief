from __future__ import annotations
from pydantic import BaseModel
from typing import Optional, Any

class ResponseBase(BaseModel):
    code: int = 0
    message: str = "ok"
    data: Optional[Any] = None

class Pagination(BaseModel):
    page: int = 1
    page_size: int = 20
    total: int = 0