"""
Announcement routes (user read + admin manage)
"""

from __future__ import annotations
from typing import List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user, get_admin_user
from app.models.user import User
from app.models.announcement import Announcement
from app.schemas.admin import AnnouncementCreate, AnnouncementOut

router = APIRouter(prefix="/announcements", tags=["announcements"])


@router.get("/", response_model=List[AnnouncementOut])
async def list_active_announcements(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get active announcements for users"""
    anns = db.query(Announcement).filter(Announcement.erased_at.is_(None)).order_by(
        Announcement.is_pinned.desc(), Announcement.published_at.desc()
    ).all()
    return anns


# --- Admin ---

@router.post("/", response_model=AnnouncementOut, dependencies=[Depends(get_admin_user)])
async def create_announcement(req: AnnouncementCreate, db: Session = Depends(get_db)):
    ann = Announcement(**req.model_dump())
    db.add(ann)
    db.commit()
    db.refresh(ann)
    return ann


@router.get("/all", response_model=List[AnnouncementOut], dependencies=[Depends(get_admin_user)])
async def list_all_announcements(db: Session = Depends(get_db)):
    return db.query(Announcement).order_by(Announcement.created_at.desc()).all()


@router.put("/{ann_id}/erase", dependencies=[Depends(get_admin_user)])
async def erase_announcement(ann_id: int, db: Session = Depends(get_db)):
    ann = db.query(Announcement).get(ann_id)
    if not ann:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Announcement not found")
    ann.erased_at = datetime.utcnow()
    db.commit()
    return {"message": "OK"}


@router.delete("/{ann_id}", dependencies=[Depends(get_admin_user)])
async def delete_announcement(ann_id: int, db: Session = Depends(get_db)):
    ann = db.query(Announcement).get(ann_id)
    if not ann:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Announcement not found")
    db.delete(ann)
    db.commit()
    return {"message": "OK"}
