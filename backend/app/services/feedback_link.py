"""邮件「有用 / 没用」反馈链接的签名与限频（t110）

旧链接只有 ?rid=&v=，rid 是连续数字、无需登录，任何人都能批量刷；
邮件安全扫描预取链接时也会被当成一次点击。现在：
- 链接带 HMAC 签名 s（绑定 report_id + user_id），伪造或改 rid 都会失效；
- GET 只展示确认页，真正写入走 POST（页面脚本自动提交；扫描器一般不执行脚本）；
- 每份报告只保留一条反馈，重复点击改为更新，不再新增；
- 每份报告简单限频（进程内），防止脚本对同一链接反复提交。
"""
from __future__ import annotations

import hashlib
import hmac
import threading
import time
from collections import deque
from datetime import datetime

from app.config import get_settings

# 这个时间之前生成的报告，邮件里是旧版无签名链接：仍然接受（但同样只记一条、同样限频）
LEGACY_UNSIGNED_BEFORE = datetime(2026, 11, 16)

RATE_LIMIT = 20          # 每份报告在窗口内最多提交次数
RATE_WINDOW = 600        # 秒

_hits: dict[str, deque] = {}
_lock = threading.Lock()


def sign(report_id: int, user_id: int | None) -> str:
    key = get_settings().secret_key.encode()
    msg = f"fb:{int(report_id)}:{int(user_id or 0)}".encode()
    return hmac.new(key, msg, hashlib.sha256).hexdigest()[:24]


def build_url(base: str, report_id: int, user_id: int | None, value: str) -> str:
    return f"{base}/api/v1/reports/feedback?rid={int(report_id)}&v={value}&s={sign(report_id, user_id)}"


def is_valid(report, s: str | None) -> bool:
    if s:
        return hmac.compare_digest(str(s), sign(report.id, report.user_id))
    created = getattr(report, "created_at", None)
    return bool(created and created < LEGACY_UNSIGNED_BEFORE)


def allow(key: str, now: float | None = None) -> bool:
    now = time.time() if now is None else now
    with _lock:
        q = _hits.setdefault(key or "?", deque())
        while q and now - q[0] > RATE_WINDOW:
            q.popleft()
        if len(q) >= RATE_LIMIT:
            return False
        q.append(now)
        return True
