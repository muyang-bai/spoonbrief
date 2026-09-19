from __future__ import annotations
from celery import Celery
from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "hotmailbrief",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "app.tasks.email_tasks",
        "app.tasks.schedule_tasks",
        "app.tasks.report_tasks",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    broker_connection_retry_on_startup=True,
    task_time_limit=900,        # 硬超时 15 分钟（防任务挂死占住 worker）
    task_soft_time_limit=600,   # 软超时 10 分钟
    beat_schedule={
        "check-scheduled-reports": {
            # 注意：必须与任务注册名一致（@celery_app.task(name="check_and_dispatch")），
            # 否则 worker 报 unregistered task 并丢弃消息（曾导致定时发送全部失效）
            "task": "check_and_dispatch",
            "schedule": 60.0,   # 每分钟检查一次
        },
        "watchdog-recover": {
            "task": "watchdog",
            "schedule": 900.0,  # 每 15 分钟自愈孤儿任务 + 失败统计
        },
        "news-pool-ingest": {
            "task": "ingest_news_pool",
            "schedule": 1800.0,  # 每 30 分钟信息池抓取（生产本地调度器已关闭，必须由 beat 承担）
        },
    },
)