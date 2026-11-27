#!/usr/bin/env bash
# ════════════════════════════════════════════════════════════
# 恢复本脚本自己打出来的 PostgreSQL 备份：
#   bash deploy/restore.sh /root/backups/hotmailbrief/db_XXXX.sql.gz
# 当前生产是宿主机 MySQL，不能用这个脚本恢复现网库。
# ════════════════════════════════════════════════════════════
set -euo pipefail
cd "$(dirname "$0")/.."

BACKUP_FILE="${1:?用法: bash deploy/restore.sh <备份文件路径>}"
[ -f "$BACKUP_FILE" ] || { echo "[错误] 备份文件不存在: $BACKUP_FILE"; exit 1; }

set -a; source .env; set +a

echo "==> 停止生成任务（避免恢复期间写入）"
docker compose stop celery-worker celery-beat || true

echo "==> 恢复数据库"
gunzip -c "$BACKUP_FILE" | docker compose exec -T postgres \
  psql -U "${POSTGRES_USER:-hotmail}" -d "${POSTGRES_DB:-hotmailbrief}"

echo "==> 重启任务"
docker compose start celery-worker celery-beat

echo "✅ 恢复完成"
