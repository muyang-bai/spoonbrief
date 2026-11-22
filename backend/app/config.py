"""
全局配置管理 —— 基于 pydantic-settings，从 .env 读取
"""

from __future__ import annotations
from functools import lru_cache
from typing import List
from urllib.parse import quote_plus

from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # ── 应用 ──
    app_name: str = "一勺热点"
    app_env: str = "development"
    app_url: str = "http://localhost:8000"
    secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440
    default_tz: str = "Asia/Shanghai"

    # ── 数据库 ──
    use_sqlite: bool = False
    database_url: str = ""  # 可选显式连接串（如 sqlite:///./hotmailbrief.db）；为空时按 use_sqlite 推导
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_user: str = "hotmail"
    postgres_password: str = "hotmailpwd123"
    postgres_db: str = "hotmailbrief"

    @property
    def database_url_resolved(self) -> str:
        if self.database_url:
            return self.database_url
        if self.use_sqlite:
            return "sqlite:///./hotmailbrief.db"
        # 密码必须 URL 编码：含 @ : / 等特殊字符会破坏连接串解析（曾导致 host 被解析成 "@postgres"）
        return (
            f"postgresql+psycopg2://{quote_plus(self.postgres_user)}:{quote_plus(self.postgres_password)}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def async_database_url(self) -> str:
        if self.database_url:
            return self.database_url.replace("sqlite:///", "sqlite+aiosqlite:///", 1)
        if self.use_sqlite:
            return "sqlite+aiosqlite:///./hotmailbrief.db"
        return (
            f"postgresql+asyncpg://{quote_plus(self.postgres_user)}:{quote_plus(self.postgres_password)}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    # ── 调度器 ──
    # 本地模式：进程内 APScheduler；生产模式（Celery beat/worker）下应设为 false
    enable_local_scheduler: bool = True

    # ── Redis ──
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: str = ""

    @property
    def redis_url(self) -> str:
        pwd = f":{quote_plus(self.redis_password)}@" if self.redis_password else ""
        return f"redis://{pwd}{self.redis_host}:{self.redis_port}/0"

    # ── 加密 ──
    encryption_key: str = ""

    # ── SMTP ──
    smtp_host: str = ""
    smtp_port: int = 465
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from_email: str = ""
    smtp_from_name: str = "一勺热点"
    smtp_use_ssl: bool = True

    # ── AI ──
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-v4-flash"
    volcano_api_key: str = ""
    volcano_base_url: str = "https://ark.cn-beijing.volces.com/api/v3"
    volcano_model: str = ""
    ai_default_provider: str = "deepseek"
    ai_enabled: bool = True

    # ── 信息源 ──
    newsapi_key: str = ""
    bing_news_key: str = ""
    dailyhot_base_url: str = "https://api.v2.aicfe.cn"

    # ── 人机验证 ──
    hcaptcha_site_key: str = ""
    hcaptcha_secret: str = ""

    # ── 管理员 ──
    admin_nickname: str = "MuYang-白"
    admin_email: str = ""
    admin_init_password: str = ""

    # ── CORS ──
    cors_origins: str = "http://localhost:5173"

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    # ── Sentry ──
    sentry_dsn: str = ""

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

@lru_cache
def get_settings() -> Settings:
    return Settings()