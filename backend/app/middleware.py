"""
安全中间件：限流 + 安全头 + 反爬
"""
from __future__ import annotations
import time, hashlib
from collections import defaultdict
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, JSONResponse


# ── 内存限流（简单版，生产建议用 Redis）──
_rate_limit_store: dict[str, list[float]] = defaultdict(list)
_RATE_LIMIT_WINDOW = 60       # 窗口秒数
_RATE_LIMIT_MAX = 120         # 窗口内最大请求数
_WHITELIST_PATHS = {"/health", "/api/v1/public/", "/docs", "/openapi.json", "/favicon.ico"}


class RateLimitMiddleware(BaseHTTPMiddleware):
    """基于 IP + User-Agent 的简单限流"""

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # 跳过白名单路径
        for wp in _WHITELIST_PATHS:
            if path.startswith(wp):
                return await call_next(request)

        # 生成限流键：IP + UA 哈希
        client_ip = request.client.host if request.client else "unknown"
        ua = request.headers.get("user-agent", "")
        key = hashlib.md5(f"{client_ip}:{ua}".encode()).hexdigest()[:12]

        now = time.time()
        # 清理过期记录
        _rate_limit_store[key] = [t for t in _rate_limit_store[key] if now - t < _RATE_LIMIT_WINDOW]

        if len(_rate_limit_store[key]) >= _RATE_LIMIT_MAX:
            return JSONResponse(
                status_code=429,
                content={"detail": "请求过于频繁，请稍后再试", "retry_after": _RATE_LIMIT_WINDOW},
            )

        _rate_limit_store[key].append(now)
        return await call_next(request)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """添加安全响应头"""

    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        # 生产环境启用 HSTS
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        # 移除服务器标识
        if "server" in response.headers:
            del response.headers["server"]
        return response


class AntiBotMiddleware(BaseHTTPMiddleware):
    """简单反爬：检测异常请求模式"""

    _ua_blocklist = [
        "sqlmap", "nikto", "nmap", "masscan", "zgrab",
        "python-requests/", "Go-http-client/",
        "libwww-perl", "wget", "HTTrack", "scrapy",
    ]

    async def dispatch(self, request: Request, call_next):
        ua = (request.headers.get("user-agent") or "").lower()

        # 拦截已知扫描器
        for blocked in self._ua_blocklist:
            if blocked.lower() in ua:
                return Response(status_code=403, content="Forbidden")

        path = request.url.path.lower()

        # 拦截缺少 UA 的请求（但放过 health 和 API 请求）
        if not ua and not path.startswith("/health") and not path.startswith("/api/"):
            return Response(status_code=403, content="Forbidden")

        # 拦截异常路径扫描
        blocked_paths = ["/wp-admin", "/admin.php", "/.env", "/.git/", "/phpmyadmin",
                         "/config.php", "/backup", "/sql", "/.well-known/acme-challenge"]
        for bp in blocked_paths:
            if bp in path:
                return Response(status_code=404)

        return await call_next(request)
