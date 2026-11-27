# ruff: noqa: F401
# These imports are only here so the model modules register tables on
# Base.metadata before create_all. AilifeosLink and StoryMemory are registered
# by app.models but are not imported below; leave them out so this script
# still creates the same set of tables as before.

from app.database import engine, Base
from app.models.user import User
from app.models.email_address import EmailAddress
from app.models.email_verification import EmailVerificationCode
from app.models.news_source import NewsSource
from app.models.subscription import Subscription
from app.models.report import Report
from app.models.api_key import ApiKey
from app.models.system_config import SystemConfig
from app.models.prompt_template import PromptTemplate
from app.models.announcement import Announcement
from app.models.keyword_stat import KeywordStat
from app.models.compliance_text import ComplianceText
from app.models.unsubscribe_token import UnsubscribeToken
from app.models.news_item import NewsItem, NewsEvent
from app.models.task_run import TaskRun
from app.models.user_news_source import UserNewsSource
from app.models.report_feedback import ReportFeedback
from app.models.token_usage import TokenUsage

Base.metadata.create_all(bind=engine)
print("All tables created!")
