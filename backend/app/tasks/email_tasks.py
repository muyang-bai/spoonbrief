"""
邮件相关异步任务
"""

from __future__ import annotations
from loguru import logger

from app.tasks.celery_app import celery_app
from app.services.email_sender import send_email_sync



@celery_app.task(name="send_verification_email", bind=True, max_retries=3)
def send_verification_email(self, to_email: str, code: str, purpose: str = "登录、注册或重置密码"):
    """发送验证码邮件"""
    from app.services.verification_mail import render_verification_email, verification_subject

    html = render_verification_email(code, purpose)
    try:
        success = send_email_sync([to_email], verification_subject(code), html)
        if not success:
            raise Exception("发送失败")
        logger.info(f"验证码邮件已发送: {to_email}")
    except Exception as e:
        logger.error(f"验证码发送失败: {type(e).__name__}, 重试中...")
        if hasattr(self, 'retry'):
            raise self.retry(exc=e, countdown=60)


@celery_app.task(name="send_report_email", bind=True, max_retries=3)
def send_report_email(self, to_emails: list, subject: str, html_body: str):
    """发送报告邮件"""
    try:
        success = send_email_sync(to_emails, subject, html_body)
        if not success:
            raise Exception("发送失败")
        logger.info(f"报告邮件已发送: {to_emails}")
    except Exception as e:
        logger.error(f"报告发送失败: {e}, 重试中...")
        if hasattr(self, 'retry'):
            raise self.retry(exc=e, countdown=120)