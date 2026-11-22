"""
安全中间件：限流 + 安全头 + 反爬
"""
from __future__ import annotations
import time
import hashlib
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

class ResponseCacheMiddleware(BaseHTTPMiddleware):
    """登录态 GET 接口 30 秒缓存（t175）。

    多 worker 下用 Redis 共享，键里带 Authorization 哈希与全局版本号：
    - 任一写请求使版本号 +1，旧缓存整体失效（写后读一致）；
    - Redis 不可用时自动退化为进程内缓存，不影响可用性；
    - 响应头 X-Cache: HIT/MISS 便于验证。
    """

    PREFIXES = (
        "/api/v1/subscriptions", "/api/v1/reports", "/api/v1/sources",
        "/api/v1/emails", "/api/v1/profile", "/api/v1/announcements",
        "/api/v1/prompts",
    )
    TTL = 30

    def __init__(self, app):
        super().__init__(app)
        self._redis = None
        self._local = {}

    def _client(self):
        if self._redis is not None:
            return self._redis
        try:
            import redis
            from app.config import get_settings
            self._redis = redis.Redis.from_url(get_settings().redis_url, decode_responses=False, socket_timeout=1)
            self._redis.ping()
        except Exception:
            self._redis = False
        return self._redis

    @staticmethod
    def _key(auth: str, path: str, query: str) -> str:
        auth_hash = hashlib.sha256(auth.encode()).hexdigest()[:16]
        return f"api:cache:{path}:{query}:{auth_hash}"

    async def dispatch(self, request, call_next):
        path = request.url.path
        if not path.startswith(self.PREFIXES):
            return await call_next(request)

        r = self._client()
        if request.method != "GET":
            if r:
                try:
                    r.incr("api:cache:version")
                except Exception:
                    pass
            self._local.clear()
            return await call_next(request)

        auth = request.headers.get("authorization") or ""
        if not auth:
            return await call_next(request)

        key = self._key(auth, path, request.url.query)
        if r:
            try:
                ver = r.get("api:cache:version") or b"0"
                key = f"{key}:{ver.decode() if isinstance(ver, bytes) else ver}"
                hit = r.get(key)
                if hit:
                    import base64, json as _json
                    env = _json.loads(hit)
                    return Response(content=base64.b64decode(env["b"]), status_code=200,
                                    media_type=env.get("m") or "application/json",
                                    headers={"X-Cache": "HIT"})
            except Exception:
                pass
        else:
            entry = self._local.get(key)
            if entry and time.time() - entry[0] < self.TTL:
                return Response(content=entry[1], status_code=200, media_type=entry[2] or "application/json",
                                headers={"X-Cache": "HIT"})

        response = await call_next(request)
        if response.status_code != 200:
            return response

        body = b""
        async for chunk in response.body_iterator:
            body += chunk
        media = response.media_type or "application/json"
        if r:
            try:
                import base64, json as _json
                r.setex(key, self.TTL, _json.dumps({"b": base64.b64encode(body).decode(), "m": media}))
            except Exception:
                pass
        else:
            if len(self._local) > 500:
                self._local.clear()
            self._local[key] = (time.time(), body, media)
        return Response(content=body, status_code=200, media_type=media, headers={"X-Cache": "MISS"})
