"""
hCaptcha 人机验证校验
"""

from __future__ import annotations
import httpx

from app.config import get_settings

settings = get_settings()

HCAPTCHA_VERIFY_URL = "https://api.hcaptcha.com/siteverify"

async def verify_captcha(token: str) -> bool:
    """
    向 hCaptcha 校验用户提交的 token
    """
    if not settings.hcaptcha_secret:
        # ---
        return True

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            HCAPTCHA_VERIFY_URL,
            data={
                "secret": settings.hcaptcha_secret,
                "response": token,
            },
        )
        result = resp.json()
        return result.get("success", False)