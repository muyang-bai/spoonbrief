"""
邮件发送服务（兼容 QQ/163/Gmail 等 SMTP）
配置优先级：管理员后台(system_config) > .env 兜底
"""

from __future__ import annotations
import smtplib
import asyncio
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header
from email.utils import formataddr
from typing import Optional, List, Dict
from loguru import logger

from bs4 import BeautifulSoup

from app.config import get_settings
from app.utils.secrets import unseal

settings = get_settings()


def _effective_smtp_config() -> Dict:
    """读取 SMTP 配置：数据库 system_config 优先，.env 兜底（保证后台修改生效）"""
    cfg = {
        "host": settings.smtp_host,
        "port": settings.smtp_port,
        "user": settings.smtp_user,
        "password": settings.smtp_password,
        "from_email": settings.smtp_from_email,
        "from_name": settings.smtp_from_name,
        "use_ssl": settings.smtp_use_ssl,
    }
    try:
        from app.database import SessionLocal
        from app.models.system_config import SystemConfig
        db = SessionLocal()
        try:
            rows = db.query(SystemConfig).filter(SystemConfig.key.like("smtp_%")).all()
            db_cfg = {c.key.replace("smtp_", ""): c.value for c in rows}
            if db_cfg.get("host"):
                cfg["host"] = db_cfg.get("host")
            if db_cfg.get("port"):
                cfg["port"] = int(db_cfg["port"])
            if db_cfg.get("user"):
                cfg["user"] = db_cfg.get("user")
            if db_cfg.get("password"):
                cfg["password"] = unseal(db_cfg.get("password"))
            if db_cfg.get("from_email"):
                cfg["from_email"] = db_cfg.get("from_email")
            if db_cfg.get("from_name"):
                cfg["from_name"] = db_cfg.get("from_name")
            if db_cfg.get("use_ssl") is not None:
                cfg["use_ssl"] = db_cfg.get("use_ssl").lower() in ("true", "1", "yes")
        finally:
            db.close()
    except Exception as e:  # 数据库不可用时回退 env
        logger.warning(f"读取 SMTP 数据库配置失败，使用 .env 兜底: {e}")
    return cfg


def _html_to_text(html_body: str) -> str:
    """HTML 转纯文本（邮件备选部分）"""
    try:
        return BeautifulSoup(html_body, "html.parser").get_text("\n", strip=True)
    except Exception:
        return html_body


def _send_sync(
    to_emails: List[str],
    subject: str,
    html_body: str,
    from_email: str,
    from_name: str,
) -> bool:
    """同步 SMTP 发送（在线程池中执行）"""
    cfg = _effective_smtp_config()
    host = cfg["host"]
    if not host or not from_email:
        logger.warning("SMTP 未配置，跳过邮件发送")
        return False

    message = MIMEMultipart("alternative")
    message["From"] = formataddr((str(Header(from_name or "", "utf-8")), from_email))
    message["To"] = ", ".join(to_emails)
    message["Subject"] = Header(subject, "utf-8")
    # 纯文本备选 + HTML 正文（提高送达兼容性）
    message.attach(MIMEText(_html_to_text(html_body), "plain", "utf-8"))
    message.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        if cfg["use_ssl"]:
            server = smtplib.SMTP_SSL(host, cfg["port"], timeout=30)
        else:
            server = smtplib.SMTP(host, cfg["port"], timeout=30)
            server.starttls()

        server.login(cfg["user"] or from_email, cfg["password"])
        server.sendmail(from_email, to_emails, message.as_string())
        server.quit()

        logger.info(f"邮件发送成功: {len(to_emails)} 位收件人")
        return True
    except smtplib.SMTPAuthenticationError:
        logger.error("SMTP 认证失败（请检查邮箱地址和授权码是否正确）")
        return False
    except Exception as e:
        logger.error(f"邮件发送失败: {type(e).__name__}")
        return False


async def send_email(
    to_emails: List[str],
    subject: str,
    html_body: str,
    from_email: Optional[str] = None,
    from_name: Optional[str] = None,
) -> bool:
    """异步发送邮件（在线程池中执行同步 SMTP 调用）"""
    cfg = _effective_smtp_config()
    from_addr = from_email or cfg["from_email"]
    display_name = from_name or cfg["from_name"]
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None, _send_sync, to_emails, subject, html_body, from_addr, display_name
    )


def send_email_sync(
    to_emails: List[str],
    subject: str,
    html_body: str,
    from_email: Optional[str] = None,
    from_name: Optional[str] = None,
) -> bool:
    """同步发送（供 Celery 任务调用）"""
    cfg = _effective_smtp_config()
    from_addr = from_email or cfg["from_email"]
    display_name = from_name or cfg["from_name"]
    return _send_sync(to_emails, subject, html_body, from_addr, display_name)
