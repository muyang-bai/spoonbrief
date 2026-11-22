# ════════════════════════════════════════════════════════════
# 一勺热点 生产镜像（多阶段）
# 同一镜像可运行 4 种角色：backend / celery-worker / celery-beat / frontend
# ════════════════════════════════════════════════════════════

# ── 阶段 1：构建前端 ──
FROM node:20-alpine AS frontend-build
WORKDIR /build
COPY frontend/package.json frontend/vite.config.js* frontend/index.html* ./
COPY frontend/public ./public
COPY frontend/src ./src
RUN npm config set registry https://registry.npmmirror.com && npm install --no-audit --no-fund && npm run build

# ── 阶段 2：Python 运行时 ──
FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app

# 系统依赖（时区数据 + 健康检查用 curl；psycopg2/asyncpg 均有预编译 wheel，无需 build-essential）
# 国内服务器走清华 Debian 镜像，避免 apt 卡在 deb.debian.org
RUN set -eux; \
    if [ -f /etc/apt/sources.list.d/debian.sources ]; then \
        sed -i 's|deb.debian.org|mirrors.tuna.tsinghua.edu.cn|g; s|security.debian.org|mirrors.tuna.tsinghua.edu.cn|g' /etc/apt/sources.list.d/debian.sources; \
    fi; \
    if [ -f /etc/apt/sources.list ]; then \
        sed -i 's|deb.debian.org|mirrors.tuna.tsinghua.edu.cn|g; s|security.debian.org|mirrors.tuna.tsinghua.edu.cn|g' /etc/apt/sources.list; \
    fi; \
    apt-get update -o Acquire::Retries=3 -o Acquire::http::Timeout=30; \
    apt-get install -y --no-install-recommends -o Acquire::Retries=3 -o Acquire::http::Timeout=30 \
        tzdata curl; \
    rm -rf /var/lib/apt/lists/*

# 依赖（国内服务器走清华 PyPI 镜像）
COPY backend/requirements.txt backend/requirements-prod.txt ./
RUN pip install --no-cache-dir -r requirements-prod.txt \
    -i https://pypi.tuna.tsinghua.edu.cn/simple \
    --trusted-host pypi.tuna.tsinghua.edu.cn

# 后端代码 + 前端构建产物 + 静态服务器 + 迁移工具 + 预渲染页
COPY backend/app ./app
COPY backend/create_tables.py backend/init_admin.py ./
COPY deploy/migrate_sqlite_to_pg.py ./
COPY --from=frontend-build /build/dist ./frontend/dist
COPY prerendered ./prerendered
COPY serve_frontend.py ./

# 生产角色默认命令（compose 会覆盖）
CMD ["gunicorn", "-w", "2", "-k", "uvicorn.workers.UvicornWorker", "app.main:app", "-b", "0.0.0.0:8000", "--timeout", "300", "--graceful-timeout", "60"]
