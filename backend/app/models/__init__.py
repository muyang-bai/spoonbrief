from __future__ import annotations
from app.models.user import User
from app.models.email_address import EmailAddress
from app.models.subscription import Subscription
from app.models.news_source import NewsSource
from app.models.report import Report
from app.models.announcement import Announcement
from app.models.prompt_template import PromptTemplate
from app.models.api_key import ApiKey
from app.models.keyword_stat import KeywordStat
from app.models.system_config import SystemConfig
from app.models.compliance_text import ComplianceText
from app.models.email_verification import EmailVerificationCode
from app.models.unsubscribe_token import UnsubscribeToken   # ← 新增
from app.models.news_item import NewsItem, NewsEvent        # 信息池
from app.models.task_run import TaskRun                     # 任务持久化
from app.models.user_news_source import UserNewsSource      # 用户自定义信息源

__all__ = [
    "User", "EmailAddress", "Subscription", "NewsSource",
    "Report", "Announcement", "PromptTemplate", "ApiKey",
    "KeywordStat", "SystemConfig", "ComplianceText",
    "EmailVerificationCode", "UnsubscribeToken",            # ← 新增
    "NewsItem", "NewsEvent", "TaskRun", "UserNewsSource",
]
