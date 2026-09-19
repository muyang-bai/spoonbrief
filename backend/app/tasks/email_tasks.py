"""
邮件相关异步任务
"""

from __future__ import annotations
import asyncio
from loguru import logger

from app.tasks.celery_app import celery_app
from app.services.email_sender import send_email_sync
from app.config import get_settings

settings = get_settings()


@celery_app.task(name="send_verification_email", bind=True, max_retries=3)
def send_verification_email(self, to_email: str, code: str):
    """发送验证码邮件"""
    # 本地开发模式：SMTP 未配置时直接打印验证码
    if not settings.smtp_host:
        logger.info("=" * 50)
        logger.info(f"[DEV] 验证码邮件 -> {to_email}")
        logger.info(f"[DEV] 验证码: {code}")
        logger.info("=" * 50)
        return

    html = f"""
    <div style="font-family:sans-serif;max-width:400px;margin:0 auto;padding:32px;text-align:center;">
      <h2 style="color:#764ba2;">一勺热点 验证码</h2>
      <p style="font-size:14px;color:#666;">您的验证码是：</p>
      <p style="font-size:36px;font-weight:700;color:#333;letter-spacing:8px;margin:16px 0;">{code}</p>
      <p style="font-size:12px;color:#999;">5 分钟内有效</p>
    </div>
    """
    try:
        success = send_email_sync([to_email], "一勺热点 验证码", html)
        if not success:
            raise Exception("发送失败")
        logger.info(f"验证码邮件已发送: {to_email}")
    except Exception as e:
        logger.error(f"验证码发送失败: {e}, 重试中...")
        if hasattr(self, 'retry'):
            raise self.retry(exc=e, countdown=60)


@celery_app.task(name="send_report_email", bind=True, max_retries=3)
def send_report_email(self, to_emails: list, subject: str, html_body: str):
    """发送报告邮件"""
    if not settings.smtp_host:
        logger.info(f"[DEV] 报告邮件 -> {to_emails} | {subject}")
        logger.info(f"[DEV] HTML 长度: {len(html_body)}")
        return

    try:
        success = send_email_sync(to_emails, subject, html_body)
        if not success:
            raise Exception("发送失败")
        logger.info(f"报告邮件已发送: {to_emails}")
    except Exception as e:
        logger.error(f"报告发送失败: {e}, 重试中...")
        if hasattr(self, 'retry'):
            raise self.retry(exc=e, countdown=120)