"""报告发送后，把简报推送到 AiLifeOS（HMAC 服务间鉴权）。"""
from __future__ import annotations
import hashlib
import hmac
import json
import os
import time
import uuid
import urllib.request

from sqlalchemy import text


def notify_brief(db, user_id: int, report) -> None:
    base = (os.getenv("AILIFEOS_BASE_URL") or "").rstrip("/")
    secret = os.getenv("INTEGRATION_HMAC_SECRET") or ""
    if not base or not secret:
        return
    try:
        row = db.execute(text("SELECT ailifeos_uid FROM ailifeos_links WHERE user_id=:id"), {"id": user_id}).first()
        uid = row[0] if row else None
        if not uid:
            print('hook: no ailifeos_uid for user', user_id)
            return
        payload = {
            "uid": uid,
            "report_id": str(report.id),
            "title": (report.subject or "一勺热点简报")[:200],
            "summary": (report.ai_analysis_html or "")[:1500],
            "url": "",
        }
        body = json.dumps(payload, ensure_ascii=False).encode()
        path = "/internal/v1/briefs"
        ts, nonce = str(int(time.time())), str(uuid.uuid4())
        canon = f"POST\n{path}\n{ts}\n{nonce}\n" + hashlib.sha256(body).hexdigest()
        sig = hmac.new(secret.encode(), canon.encode(), hashlib.sha256).hexdigest()
        req = urllib.request.Request(base + path, data=body, method="POST", headers={
            "Content-Type": "application/json", "X-Client-Id": "hotbrief",
            "X-Timestamp": ts, "X-Nonce": nonce, "X-Signature": sig,
        })
        urllib.request.urlopen(req, timeout=5).read()
    except Exception as failure:
        from loguru import logger
        logger.warning(f"ailifeos hook failed: {failure}")
