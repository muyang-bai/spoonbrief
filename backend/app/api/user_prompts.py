"""
用户 Skill（Prompt 模板）管理
平台模板：只可选不可编辑 / 开源模板：所有人可用 / 私有模板：仅作者
"""
from __future__ import annotations
import json
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.deps import get_current_user
from app.models.user import User
from app.models.prompt_template import PromptTemplate
from app.schemas.user import UserPromptCreate, UserPromptUpdate, SkillImportRequest

router = APIRouter(prefix="/prompts", tags=["Skill模板"])


def _mask_platform(tpl: PromptTemplate) -> dict:
    """平台模板：隐藏 system_prompt 和 user_prompt_template"""
    return dict(
        id=tpl.id, name=tpl.name, description=tpl.description or "平台官方模板，由管理员维护",
        system_prompt="", user_prompt_template="",
        model=tpl.model, temperature=tpl.temperature, max_tokens=tpl.max_tokens,
        is_default=tpl.is_default, is_active=tpl.is_active,
        is_platform=True, is_open_source=tpl.is_open_source,
        suitable_for=tpl.suitable_for, tags=tpl.tags, usage_hint=tpl.usage_hint,
        owner_id=None, created_at=str(tpl.created_at) if tpl.created_at else None,
    )


def _to_dict(tpl: PromptTemplate, mask_internals: bool = False) -> dict:
    if tpl.is_platform and mask_internals:
        return _mask_platform(tpl)
    return dict(
        id=tpl.id, name=tpl.name, description=tpl.description or "",
        system_prompt=tpl.system_prompt, user_prompt_template=tpl.user_prompt_template,
        model=tpl.model, temperature=tpl.temperature, max_tokens=tpl.max_tokens,
        is_default=tpl.is_default, is_active=tpl.is_active,
        is_platform=tpl.is_platform, is_open_source=tpl.is_open_source,
        suitable_for=tpl.suitable_for, tags=tpl.tags, usage_hint=tpl.usage_hint,
        owner_id=tpl.owner_id, created_at=str(tpl.created_at) if tpl.created_at else None,
    )


@router.get("/")
async def list_prompts(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """三栏列表：平台模板 + 开源模板 + 我的模板（开源模板含官方开源的，允许同时出现在两栏）"""
    platform = db.query(PromptTemplate).filter(
        PromptTemplate.is_platform == True, PromptTemplate.is_active == True
    ).order_by(PromptTemplate.created_at.desc()).all()

    open_source = db.query(PromptTemplate).filter(
        PromptTemplate.is_open_source == True, PromptTemplate.is_active == True,
    ).order_by(PromptTemplate.created_at.desc()).all()

    my = db.query(PromptTemplate).filter(
        PromptTemplate.owner_id == user.id, PromptTemplate.is_active == True,
        PromptTemplate.is_platform == False,
    ).order_by(PromptTemplate.created_at.desc()).all()

    return {
        "platform": [_mask_platform(t) for t in platform],
        "open_source": [_to_dict(t) for t in open_source],
        "my": [_to_dict(t) for t in my],
    }


@router.get("/{tpl_id}")
async def get_prompt(tpl_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    tpl = db.get(PromptTemplate, tpl_id)
    if not tpl:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "模板不存在")
    if tpl.is_platform:
        return _mask_platform(tpl)
    if tpl.is_open_source:
        return _to_dict(tpl)
    if tpl.owner_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "无权查看此模板")
    return _to_dict(tpl)


@router.post("/")
async def create_prompt(data: UserPromptCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """新建 Skill 模板"""
    if not data.name.strip():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "模板名称不能为空")
    if not data.system_prompt.strip():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "System Prompt（角色设定）不能为空")

    payload = data.model_dump()
    payload.update(owner_id=user.id, is_platform=False)
    tpl = PromptTemplate(**payload)
    db.add(tpl)
    db.commit()
    db.refresh(tpl)
    return _to_dict(tpl)


@router.put("/{tpl_id}")
async def update_prompt(tpl_id: int, data: UserPromptUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    tpl = db.get(PromptTemplate, tpl_id)
    if not tpl or tpl.owner_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "模板不存在或无权编辑")
    if tpl.is_platform:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "平台模板不可编辑")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(tpl, field, value)
    db.commit()
    db.refresh(tpl)
    return _to_dict(tpl)


@router.delete("/{tpl_id}")
async def delete_prompt(tpl_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    tpl = db.get(PromptTemplate, tpl_id)
    if not tpl or tpl.owner_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "模板不存在或无权操作")
    if tpl.is_platform:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "平台模板不可删除")
    db.delete(tpl)
    db.commit()
    return {"message": "模板已删除"}


# ═══ 导出 ═══
@router.get("/{tpl_id}/export")
async def export_prompt(tpl_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    tpl = db.get(PromptTemplate, tpl_id)
    if not tpl:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "模板不存在")
    # 平台模板仅在"未开源"时禁止导出；已开源的官方模板与用户开源模板一样可下载导入
    if tpl.is_platform and not tpl.is_open_source:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "该模板为平台内置模板，不支持导出")
    if tpl.owner_id != user.id and not tpl.is_open_source:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "无权导出此模板")

    from app.models.user import User as UserModel
    author = db.get(UserModel, tpl.owner_id) if tpl.owner_id else None
    skill = {
        "schema": "spoonbrief-skill-v1",
        "name": tpl.name,
        "description": tpl.description or "",
        "system_prompt": tpl.system_prompt,
        "user_prompt_template": tpl.user_prompt_template,
        "model": tpl.model,
        "temperature": tpl.temperature,
        "max_tokens": tpl.max_tokens,
        "suitable_for": tpl.suitable_for or "",
        "tags": tpl.tags or "",
        "usage_hint": tpl.usage_hint or "",
        "author": author.nickname if author else "未知",
        "exported_at": datetime.utcnow().isoformat(),
    }
    return skill


# ═══ 导入 ═══
@router.post("/import")
async def import_prompt(data: SkillImportRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """导入 Skill JSON"""
    # 兼容旧格式 hotmail-skill-v1（品牌更名前的导出文件）
    if data.schema_version not in ("spoonbrief-skill-v1", "hotmail-skill-v1"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "不支持的 Skill 格式，请使用 .spoonskill.json 文件")
    if not data.name.strip() or not data.system_prompt.strip():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Skill 文件缺少必要字段（name/system_prompt）")

    payload = data.model_dump(exclude={"schema_version"})
    payload.update(owner_id=user.id, is_platform=False,
                   name=f"{data.name} (导入)", is_open_source=False)  # 导入的默认私有
    tpl = PromptTemplate(**payload)
    db.add(tpl)
    db.commit()
    db.refresh(tpl)
    return _to_dict(tpl)
