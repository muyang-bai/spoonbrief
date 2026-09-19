"""
数据库引擎与 Session 管理
"""

from __future__ import annotations
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base

from app.config import get_settings

settings = get_settings()

if settings.use_sqlite or settings.database_url_resolved.startswith("sqlite"):
    engine = create_engine(
        settings.database_url_resolved,
        connect_args={"check_same_thread": False},
        echo=False,
    )

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")   # 并发读写性能与一致性
        cursor.execute("PRAGMA busy_timeout=5000")  # 等待锁 5 秒而不是立即报错
        cursor.close()
else:
    engine = create_engine(
        settings.database_url_resolved,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
        echo=False,
    )

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

Base = declarative_base()

def get_db():
    """Handler"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()