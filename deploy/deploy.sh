#!/usr/bin/env bash
# ════════════════════════════════════════════════════════════
# 一勺热点 本地构建脚本：docker compose build && up，镜像标签 hotmailbrief:latest。
# 不是现网更新命令。现网必须叠两个 overlay（见 README），否则前端会用到
# 生产主机上的 hotmailbrief:latest，而那个标签是后端镜像。
# 用法: bash deploy/deploy.sh
# ════════════════════════════════════════════════════════════
set -euo pipefail
cd "$(dirname "$0")/.."

echo "==> [1/5] 检查 .env"
if [ ! -f .env ]; then
  echo "[错误] 缺少 .env：请把 backend/.env.example 复制为仓库根目录 .env，并确认:"
  echo "       DATABASE_URL（MySQL）  REDIS_HOST=redis  ENABLE_LOCAL_SCHEDULER=false"
  exit 1
fi

echo "==> [2/5] 构建镜像（前端+后端多阶段）"
docker compose build

echo "==> [3/5] 启动服务"
docker compose up -d

echo "==> [4/5] 初始化数据库表 + 管理员（幂等，可重复执行）"
docker compose exec -T backend python create_tables.py
docker compose exec -T backend python -c "from init_admin import init_admin; init_admin()" || true

# 一次性数据迁移：/opt/hotmailbrief/data/hotmailbrief_backup.db 存在时执行
if [ -f data/hotmailbrief_backup.db ]; then
  echo "==> 检测到 SQLite 快照，执行迁移到 PostgreSQL"
  docker compose run --rm backend python migrate_sqlite_to_pg.py /app/data/hotmailbrief_backup.db
  mv data/hotmailbrief_backup.db data/hotmailbrief_backup.db.done
fi

echo "==> [5/5] 健康检查"
sleep 5
curl -fsS http://127.0.0.1:8080/health && echo ""
docker compose ps
echo ""
echo "✅ 部署完成。宿主机 nginx 指向 127.0.0.1:8080"
echo "   查看日志: docker compose logs -f --tail=100 backend celery-worker celery-beat"
