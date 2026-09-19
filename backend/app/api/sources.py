"""
信息源路由（用户端只读 + 用户自定义源增删 + 管理员增删改）
"""

from __future__ import annotations
import re
from typing import List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user, get_admin_user
from app.models.user import User
from app.models.news_source import NewsSource
from app.models.user_news_source import UserNewsSource
from app.schemas.source import NewsSourceCreate, NewsSourceUpdate, NewsSourceOut

router = APIRouter(prefix="/sources", tags=["admin"])

# ── 用户自定义 RSS 源 ──

class UserSourceCreate(BaseModel):
    name: str
    url: str
    category: str = "自定义"

class UserSourceOut(BaseModel):
    id: int
    name: str
    url: str
    category: str
    is_active: bool
    last_fetch_at: datetime | None
    last_error: str | None
    created_at: datetime

    class Config:
        from_attributes = True

_URL_RE = re.compile(r"^https?://[^\s]+$")

@router.get("/custom", response_model=List[UserSourceOut])
async def list_custom_sources(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """我的自定义信息源列表"""
    return db.query(UserNewsSource).filter(UserNewsSource.user_id == user.id).order_by(UserNewsSource.id.desc()).all()

@router.post("/custom", response_model=UserSourceOut, status_code=201)
async def create_custom_source(req: UserSourceCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """添加自定义 RSS 源（个人使用，不进入公共池）"""
    if not req.name.strip():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "请填写信息源名称")
    if not _URL_RE.match(req.url.strip()):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "请输入合法的 http(s) RSS 地址")
    if len(db.query(UserNewsSource).filter(UserNewsSource.user_id == user.id).all()) >= 10:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "自定义信息源最多 10 个")

    # 校验 RSS 可用性（拉一次验证）
    import feedparser, httpx
    try:
        resp = httpx.get(req.url.strip(), headers={"User-Agent": "Mozilla/5.0"}, timeout=15, follow_redirects=True)
        if resp.status_code != 200:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"地址无法访问（HTTP {resp.status_code}）")
        feed = feedparser.parse(resp.content)
        if not feed.entries:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "该地址不是有效的 RSS 订阅源（未解析到内容）")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"地址校验失败：{str(e)[:80]}")

    src = UserNewsSource(user_id=user.id, name=req.name.strip(), url=req.url.strip(), category=req.category or "自定义")
    db.add(src)
    db.commit()
    db.refresh(src)
    return src

@router.delete("/custom/{source_id}")
async def delete_custom_source(source_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    src = db.query(UserNewsSource).filter(UserNewsSource.id == source_id, UserNewsSource.user_id == user.id).first()
    if not src:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "自定义信息源不存在")
    db.delete(src)
    db.commit()
    return {"message": "已删除"}

# ── 平台源（用户只读） ──

@router.get("/", response_model=List[NewsSourceOut])
async def list_sources(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Handler"""
    sources = db.query(NewsSource).filter(NewsSource.is_active == True).all()
    return sources

# ── 管理员 ──

@router.post("/", response_model=NewsSourceOut, dependencies=[Depends(get_admin_user)])
async def create_source(req: NewsSourceCreate, db: Session = Depends(get_db)):
    source = NewsSource(**req.model_dump())
    db.add(source)
    db.commit()
    db.refresh(source)
    return source

@router.put("/{source_id}", response_model=NewsSourceOut, dependencies=[Depends(get_admin_user)])
async def update_source(source_id: int, req: NewsSourceUpdate, db: Session = Depends(get_db)):
    source = db.query(NewsSource).get(source_id)
    if not source:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "信息源不存在，可能已被删除")
    for k, v in req.model_dump(exclude_unset=True).items():
        setattr(source, k, v)
    db.commit()
    db.refresh(source)
    return source


@router.delete("/{source_id}", dependencies=[Depends(get_admin_user)])
async def delete_source(source_id: int, db: Session = Depends(get_db)):
    source = db.query(NewsSource).get(source_id)
    if not source:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "信息源不存在，可能已被删除")
    db.delete(source)
    db.commit()
    return {"message": "信息源已删除"}
