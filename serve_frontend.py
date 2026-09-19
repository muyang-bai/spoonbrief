# -*- coding: utf-8 -*-
"""
前端静态服务器（本地开发 & Docker 容器通用）
- 托管 frontend/dist（SPA fallback 到 index.html）
- 将 /api/* 与 /health 反向代理到后端
- 本地默认: http://127.0.0.1:3000 -> http://127.0.0.1:8000
- 容器中:  FRONTEND_PORT/HOST + BACKEND_URL + FRONTEND_DIR 由环境变量覆盖
"""
import os
import re
from aiohttp import web, ClientSession

ROOT = os.environ.get(
    "FRONTEND_DIR",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "frontend", "dist"),
)
PRERENDER_DIR = os.environ.get(
    "FRONTEND_PRERENDER_DIR",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "prerendered"),
)
BACKEND = os.environ.get("BACKEND_URL", "http://127.0.0.1:8000")
HOST = os.environ.get("FRONTEND_HOST", "127.0.0.1")
PORT = int(os.environ.get("FRONTEND_PORT", "3000"))

# 搜索引擎爬虫 UA：命中则对首页返回预渲染静态 HTML（百度不擅长执行 JS）
BOT_UA = re.compile(
    r"baiduspider|googlebot|bingbot|sogou|360spider|yandex|bytespider|"
    r"petalbot|duckduckbot|slurp|facebookexternalhit|twitterbot|smspider",
    re.IGNORECASE,
)

NO_CACHE = {"Cache-Control": "no-cache, no-store, must-revalidate"}

HOP_BY_HOP = {
    "host", "connection", "keep-alive", "proxy-authenticate",
    "proxy-authorization", "te", "trailers", "transfer-encoding",
    "upgrade", "content-length",
}


async def proxy(request: web.Request) -> web.Response:
    """将请求转发到后端"""
    headers = {k: v for k, v in request.headers.items() if k.lower() not in HOP_BY_HOP}
    headers["X-Forwarded-For"] = request.remote or ""
    body = await request.read()
    async with ClientSession() as session:
        async with session.request(
            request.method,
            BACKEND + request.path_qs,
            headers=headers,
            data=body or None,
            timeout=120,
        ) as resp:
            data = await resp.read()
            out_headers = {k: v for k, v in resp.headers.items() if k.lower() not in HOP_BY_HOP}
            return web.Response(status=resp.status, body=data, headers=out_headers)


async def static_handler(request: web.Request) -> web.Response:
    """静态文件 + SPA fallback；爬虫访问首页返回预渲染 HTML；禁止缓存"""
    rel = request.path.lstrip("/")

    # 爬虫 → 预渲染静态首页（SEO 动态渲染）
    if not rel and BOT_UA.search(request.headers.get("User-Agent", "")):
        prerendered = os.path.join(PRERENDER_DIR, "landing.html")
        if os.path.isfile(prerendered):
            return web.FileResponse(prerendered, headers=NO_CACHE)

    path = os.path.normpath(os.path.join(ROOT, rel))
    if rel and path.startswith(os.path.abspath(ROOT)) and os.path.isfile(path):
        return web.FileResponse(path, headers=NO_CACHE)
    return web.FileResponse(os.path.join(ROOT, "index.html"), headers=NO_CACHE)


app = web.Application()
app.router.add_route("*", "/health", proxy)
app.router.add_route("*", "/api", proxy)
app.router.add_route("*", "/api/{tail:.*}", proxy)
app.router.add_route("*", "/{tail:.*}", static_handler)

if __name__ == "__main__":
    print(f"[frontend] Serving {ROOT}")
    print(f"[frontend] http://{HOST}:{PORT}  ->  /api proxied to {BACKEND}")
    web.run_app(app, host=HOST, port=PORT)
