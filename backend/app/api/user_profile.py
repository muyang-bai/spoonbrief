"""
用户资料 + 画像管理（v2：结构化维度 + 可读画像文本 + 完成度 + 行为侧观察 + AI 补全）
"""

from __future__ import annotations
import json
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models.user import User
from app.schemas.user import UpdatePersonaRequest
from app.services.persona import (
    compose_persona_text, completeness, implicit_observations,
    DOMAIN_OPTIONS, GOAL_OPTIONS, CONTENT_PREF_OPTIONS, OUTPUT_OPTIONS,
    AVOID_OPTIONS, IDENTITY_OPTIONS, PERSPECTIVE_OPTIONS, HORIZON_OPTIONS,
    RISK_OPTIONS, LENGTH_OPTIONS, TONE_OPTIONS,
)

router = APIRouter(prefix="/profile", tags=["admin"])

_V2_FIELDS = (
    "field", "role_title", "goals", "domains", "content_prefs", "outputs", "avoid",
    "perspective", "horizon", "risk", "reading_length", "tone", "pain_point", "extra_notes",
)


def _load_persona(user: User) -> dict:
    if not user.persona_json:
        return {}
    try:
        data = json.loads(user.persona_json)
        return data if isinstance(data, dict) else {}
    except json.JSONDecodeError:
        return {}


@router.get("/")
async def get_profile(user: User = Depends(get_current_user)):
    return {
        "id": user.id,
        "email": user.email,
        "nickname": user.nickname,
        "role": user.role.value if hasattr(user.role, "value") else user.role,
        "persona_json": user.persona_json,
        "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None,
    }


@router.put("/persona")
async def update_persona(req: UpdatePersonaRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    persona = _load_persona(user)

    # v1 字段
    for key in ("identities", "student", "entrepreneur", "investor", "creator", "interests", "self_description"):
        val = getattr(req, key, None)
        if val is not None:
            persona[key] = val

    # v2 字段
    for key in _V2_FIELDS:
        val = getattr(req, key, None)
        if val is not None:
            persona[key] = val

    persona["_schema"] = "v2"
    persona["_updated_at"] = datetime.utcnow().isoformat()
    persona["summary"] = compose_persona_text(persona)   # 给 AI 看的可读画像（也是前端透明化预览）

    encoded = json.dumps(persona, ensure_ascii=False)
    if len(encoded) > 2000:
        raise HTTPException(400, '画像内容超出当前存储限制，请减少长文本或标签后保存（原资料未更改）')
    user.persona_json = encoded
    db.commit()
    return {
        "message": "画像已更新",
        "persona": persona,
        "completeness": completeness(persona),
    }


@router.get("/persona-meta")
async def persona_meta():
    """画像表单的选项字典（前端拉取，保证前后端口径一致）"""
    return {
        "identities": IDENTITY_OPTIONS,
        "domains": DOMAIN_OPTIONS,
        "goals": GOAL_OPTIONS,
        "content_prefs": CONTENT_PREF_OPTIONS,
        "outputs": OUTPUT_OPTIONS,
        "avoid": AVOID_OPTIONS,
        "perspective": PERSPECTIVE_OPTIONS,
        "horizon": HORIZON_OPTIONS,
        "risk": RISK_OPTIONS,
        "reading_length": LENGTH_OPTIONS,
        "tone": TONE_OPTIONS,
    }


@router.get("/persona-preview")
async def persona_preview(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """透明化：AI 实际看到的画像文本 + 完成度 + 行为侧观察（用户不用填的部分）"""
    persona = _load_persona(user)
    return {
        "persona_text": compose_persona_text(persona) or "（画像还是空的，AI 只能按通用视角分析）",
        "completeness": completeness(persona),
        "observations": implicit_observations(db, user.id),
    }


@router.post("/persona-suggest")
async def persona_suggest(user: User = Depends(get_current_user), db: Session = Depends(get_db), idempotency_key: str = Header(default="", alias="Idempotency-Key")):
    """AI 补全：结合已填画像 + 行为观察，生成画像描述与建议补充项（用户确认后再写入）"""
    import asyncio
    from loguru import logger

    persona = _load_persona(user)
    obs = implicit_observations(db, user.id)
    current = compose_persona_text(persona) or "（尚未填写）"

    system = "你是用户画像整理助手，只输出严格 JSON。"
    prompt = f"""已有画像信息：
{current}

行为观察（近 30 天）：
- 收到简报 {obs['reports']} 份，读后反馈：有用 {obs['feedback']['up']} / 没用 {obs['feedback']['down']}
- 订阅方向：{[d['keywords'] for d in obs['directions']] or '未设置'}
- 最常出现的信源：{[s['name'] for s in obs['top_sources']] or '暂无'}

请输出 JSON：
{{
  "persona_text": "用第二人称写 100 字以内的画像描述（我……），语气具体、可用于给分析模型当背景",
  "suggest": {{
    "domains": ["建议补充的 2-4 个关注赛道，从这些里选：{DOMAIN_OPTIONS}"],
    "goals": ["建议补充的目标，从这些里选：{GOAL_OPTIONS}"],
    "content_prefs": ["建议的内容偏好，从：{CONTENT_PREF_OPTIONS}"],
    "outputs": ["建议的期望输出，从：{OUTPUT_OPTIONS}"],
    "avoid": ["建议规避的内容，从：{AVOID_OPTIONS}"]
  }},
  "reason": "一句话说明为什么这样建议"
}}
不要输出任何解释文字或代码围栏。"""

    import uuid
    from app.services.credits import reserve, finish, InsufficientCredits
    request_key = idempotency_key or str(uuid.uuid4())
    if len(request_key) > 80 or not all(c.isalnum() or c in "-_." for c in request_key):
        raise HTTPException(status_code=400, detail="请求标识无效")
    credit_key = f"{user.id}:ai:{request_key}"
    try:
        operation = reserve(db, user.id, credit_key, 2)
    except InsufficientCredits:
        raise HTTPException(status_code=429, detail="积分不足：AI 补全建议需要 2 积分")
    if operation['state'] == 'committed':
        return json.loads(operation['result_json'])
    if operation['state'] == 'reserved' and operation.get('_existing'):
        raise HTTPException(status_code=409, detail="该请求正在处理中，请稍后使用同一请求重试")
    if operation['state'] != 'reserved':
        raise HTTPException(status_code=409, detail="该请求已结束，请重新主动发起")

    try:
        from app.services.ai_analyzer import get_analyzer

        an = get_analyzer()

        async def _run():
            client, model = await an._get_client(user, db, "deepseek-flash", None)
            return await an._call_llm(client, model, system, prompt, temperature=0.4, max_tokens=4000)

        text = ""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
        if loop is not None and loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                text = pool.submit(lambda: asyncio.new_event_loop().run_until_complete(_run())).result(timeout=180)
        else:
            text = asyncio.new_event_loop().run_until_complete(_run())

        if not text:
            raise HTTPException(status_code=502, detail="AI 暂时没有返回结果，请稍后再试")

        raw = text.strip()
        if raw.startswith("```"):
            raw = raw.strip("`")
            raw = raw[raw.find("{"):]
        if "{" in raw:
            raw = raw[raw.find("{"): raw.rfind("}") + 1]
        data = json.loads(raw)
        response = {
            "persona_text": str(data.get("persona_text") or "")[:400],
            "suggest": data.get("suggest") or {},
            "reason": str(data.get("reason") or "")[:120],
        }
        if not response['persona_text'] and not response['suggest']:
            raise HTTPException(status_code=502, detail="AI 没有返回有效建议，本次不扣积分")
        finish(db, user.id, credit_key, True, response)
        return response
    except HTTPException:
        finish(db, user.id, credit_key, False)
        raise
    except Exception:
        finish(db, user.id, credit_key, False)
        logger.warning("画像补全失败（积分已释放）")
        raise HTTPException(status_code=502, detail="AI 补全失败，请稍后重试")


@router.get("/quota")
async def get_quota(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    from app.services.credits import balance
    value = balance(db,user)
    return {"quota_total": value['total'], "quota_used": value['used'],
            "quota_reserved": value['reserved'], "quota_remaining": value['remaining'],
            "quota_reset_at": value['reset_at'], "is_exhausted": value['remaining'] <= 0}
