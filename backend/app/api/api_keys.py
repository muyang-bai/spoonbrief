"""
用户自有 API Key 管理
"""

from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models.user import User
from app.models.api_key import ApiKey
from app.schemas.user import ApiKeyCreate
from app.utils.crypto import encrypt_value

router = APIRouter(prefix="/api-keys", tags=["API Key"])


@router.get("/")
async def list_api_keys(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    my_keys = db.query(ApiKey).filter(ApiKey.user_id == user.id, ApiKey.is_active == True).all()
    return [{"id": k.id, "provider": k.provider, "base_url": k.base_url,
             "model": k.model, "is_active": k.is_active, "label": k.label,
             "is_platform": k.is_platform, "created_at": str(k.created_at)} for k in my_keys]


@router.post("/")
async def create_api_key(req: ApiKeyCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not req.api_key.strip():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "api_key 不能为空")
    encrypted = encrypt_value(req.api_key)
    key = ApiKey(
        user_id=user.id, provider=req.provider,
        encrypted_key=encrypted, base_url=req.base_url,
        model=req.model, label=req.label,
        is_platform=False,
    )
    db.add(key)
    db.commit()
    db.refresh(key)
    return {"id": key.id, "provider": key.provider, "model": key.model, "message": "API Key 已添加"}


@router.delete("/{key_id}")
async def delete_api_key(key_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    key = db.query(ApiKey).filter(ApiKey.id == key_id, ApiKey.user_id == user.id, ApiKey.is_platform == False).first()
    if not key:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "API Key 不存在或无权删除（平台 Key 不可删除）")
    db.delete(key)
    db.commit()
    return {"message": "API Key 已删除"}
