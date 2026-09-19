from __future__ import annotations
from fastapi import APIRouter

from app.api.auth import router as auth_router
from app.api.subscriptions import router as sub_router
from app.api.sources import router as source_router
from app.api.reports import router as report_router
from app.api.announcements import router as ann_router
from app.api.api_keys import router as apikey_router
from app.api.emails import router as email_router
from app.api.user_profile import router as profile_router
from app.api.admin import router as admin_router
from app.api.unsubscribe import router as unsubscribe_router
from app.api.user_prompts import router as user_prompts_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(sub_router)
api_router.include_router(source_router)
api_router.include_router(report_router)
api_router.include_router(ann_router)
api_router.include_router(apikey_router)
api_router.include_router(email_router)
api_router.include_router(profile_router)
api_router.include_router(user_prompts_router)
api_router.include_router(admin_router)
api_router.include_router(unsubscribe_router)