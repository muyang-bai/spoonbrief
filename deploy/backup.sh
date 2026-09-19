#!/usr/bin/env bash
# ════════════════════════════════════════════════════════════
# 每日备份：PostgreSQL 全量 + 环境配置，保留最近 7 份
# 建议 crontab：0 3 * * *  bash /opt/hotmailbrief/deploy/backup.sh >> /var/log/hbm-backup.log 2>&1
# ════════════════════════════════════════════════════════════
set -euo pipefail
cd "$(dirname "$0")/.."

set -a; source .env; set +a

BACKUP_DIR="${BACKUP_DIR:-/root/backups/hotmailbrief}"
mkdir -p "$BACKUP_DIR"
STAMP=$(date +%Y%m%d_%H%M%S)

docker compose exec -T postgres \
  pg_dump -U "${POSTGRES_USER:-hotmail}" -d "${POSTGRES_DB:-hotmailbrief}" \
  | gzip > "$BACKUP_DIR/db_${STAMP}.sql.gz"

cp .env "$BACKUP_DIR/env_${STAMP}.bak"

# 滚动保留最近 7 份
ls -1t "$BACKUP_DIR"/db_*.sql.gz  2>/dev/null | tail -n +8 | xargs -r rm -f
ls -1t "$BACKUP_DIR"/env_*.bak    2>/dev/null | tail -n +8 | xargs -r rm -f

echo "$(date '+%F %T') 备份完成: $BACKUP_DIR/db_${STAMP}.sql.gz ($(du -h "$BACKUP_DIR/db_${STAMP}.sql.gz" | cut -f1))"
