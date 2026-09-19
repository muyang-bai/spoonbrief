"""
用户资料 + 画像管理
"""

from __future__ import annotations
import json
from datetime import datetime
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models.user import User
from app.schemas.user import UserProfile, UpdatePersonaRequest

router = APIRouter(prefix="/profile", tags=["admin"])

@router.get("/", response_model=UserProfile)
async def get_profile(user: User = Depends(get_current_user)):
    return user

@router.put("/persona")
async def update_persona(req: UpdatePersonaRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    persona = {}
    if user.persona_json:
        try:
            persona = json.loads(user.persona_json)
        except json.JSONDecodeError:
            pass

    if req.identities is not None:
        persona["identities"] = req.identities
    if req.student is not None:
        persona["student"] = req.student
    if req.entrepreneur is not None:
        persona["entrepreneur"] = req.entrepreneur
    if req.investor is not None:
        persona["investor"] = req.investor
    if req.creator is not None:
        persona["creator"] = req.creator
    if req.interests is not None:
        persona["interests"] = req.interests
    if req.self_description is not None:
        persona["self_description"] = req.self_description

    # 画像版本化（便于后续结构升级与迁移）
    persona["_schema"] = "v1"
    persona["_updated_at"] = datetime.utcnow().isoformat()

    user.persona_json = json.dumps(persona, ensure_ascii=False)
    db.commit()
    return {"message": "画像已更新", "persona": persona}

@router.get("/quota")
async def get_quota(user: User = Depends(get_current_user)):
    """Get current API quota status"""
    return {
        "quota_total": user.api_quota_total,
        "quota_used": user.api_quota_used,
        "quota_remaining": max(0, user.api_quota_total - user.api_quota_used),
        "quota_reset_at": user.api_quota_reset_at.isoformat() if user.api_quota_reset_at else None,
        "is_exhausted": user.api_quota_used >= user.api_quota_total,
    }