# -*- coding: utf-8 -*-
"""
SQLite 快照 → PostgreSQL 迁移（在服务器上执行一次）
用法:
    python deploy/migrate_sqlite_to_pg.py /path/to/hotmailbrief_backup.db
说明:
    - 目标 PG 连接取自 .env（DATABASE_URL / POSTGRES_*）
    - 目标表会被清空后写入（幂等但破坏性：仅在全新部署首次执行）
    - 布尔值/JSON 自动转换，自增序列自动校正
"""
import sys
import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, ".")
import app.models  # noqa: F401  注册全部模型
# 防御性显式导入（与 create_tables.py 保持一致，防止 __init__ 遗漏）
import app.models.user  # noqa: F401
import app.models.email_address  # noqa: F401
import app.models.email_verification  # noqa: F401
import app.models.news_source  # noqa: F401
import app.models.subscription  # noqa: F401
import app.models.report  # noqa: F401
import app.models.api_key  # noqa: F401
import app.models.system_config  # noqa: F401
import app.models.prompt_template  # noqa: F401
import app.models.announcement  # noqa: F401
import app.models.keyword_stat  # noqa: F401
import app.models.compliance_text  # noqa: F401
import app.models.unsubscribe_token  # noqa: F401
import app.models.news_item  # noqa: F401
import app.models.task_run  # noqa: F401
from app.database import Base
from app.config import get_settings

# 按外键依赖排序
TABLE_ORDER = [
    "users", "email_addresses", "email_verification_codes",
    "news_sources", "prompt_templates", "system_config", "compliance_texts",
    "announcements", "keyword_stats", "api_keys", "subscriptions",
    "reports", "unsubscribe_tokens", "news_items", "news_events", "task_runs",
]


def main():
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)
    snapshot = sys.argv[1]

    settings = get_settings()
    src = sa.create_engine(f"sqlite:///{snapshot}")
    dst = sa.create_engine(settings.database_url_resolved, pool_pre_ping=True)

    meta = Base.metadata
    missing = [t for t in TABLE_ORDER if t not in meta.tables]
    if missing:
        print(f"[错误] 未知表: {missing}")
        sys.exit(1)

    total_rows = 0
    with src.connect() as s_conn, dst.begin() as d_conn:
        for tname in TABLE_ORDER:
            table = meta.tables[tname]
            rows = [dict(r._mapping) for r in s_conn.execute(sa.select(table))]
            if not rows:
                print(f"  {tname}: 0 行，跳过")
                continue
            # 类型转换：SQLite 0/1 → bool；TEXT JSON 保持字符串即可（PG 自动转换）
            for row in rows:
                for col in table.columns:
                    if isinstance(col.type, sa.Boolean) and row.get(col.name) is not None:
                        row[col.name] = bool(row[col.name])
            d_conn.execute(table.delete())           # 清空目标表
            d_conn.execute(table.insert(), rows)     # 全量写入
            total_rows += len(rows)
            print(f"  {tname}: {len(rows)} 行 ✓")

        # 自增序列校正（显式插入 id 后必须重设）
        for tname in TABLE_ORDER:
            table = meta.tables[tname]
            if "id" not in table.columns:
                continue
            d_conn.execute(sa.text(
                f"SELECT setval(pg_get_serial_sequence('{tname}', 'id'), "
                f"COALESCE((SELECT MAX(id) FROM {tname}), 1))"
            ))
        print(f"自增序列已校正")

    print(f"✅ 迁移完成，共 {total_rows} 行 -> {settings.database_url_resolved.split('@')[-1]}")


if __name__ == "__main__":
    main()
