"""
定时调度任务：每分钟检查到期订阅并派发报告生成（Celery beat 驱动）
生产可靠性要点：
- 到期超 24 小时的窗口不补发，直接滚动到下次（防重启后邮件轰炸）
- 同一订阅存在 15 分钟内的 running 任务时不再派发（防堆积）
- watchdog 每 15 分钟自愈孤儿任务（服务重启/崩溃中断的报告）
"""

from __future__ import annotations
from datetime import datetime, timedelta
from loguru import logger

from app.tasks.celery_app import celery_app
from app.tasks.report_tasks import generate_report, _update_next_sent


@celery_app.task(name="check_and_dispatch")
def check_and_dispatch():
    """每分钟检查到期订阅并派发"""
    from app.database import SessionLocal
    from app.models.subscription import Subscription
    from app.models.task_run import TaskRun

    db = SessionLocal()
    try:
        now = datetime.utcnow()
        stale_cutoff = now - timedelta(hours=24)
        running_cutoff = now - timedelta(minutes=15)
        due_subs = db.query(Subscription).filter(
            Subscription.is_active == True,
            Subscription.next_sent_at <= now,
        ).all()

        dispatched = 0
        for sub in due_subs:
            # 重启后过期窗口超过 24 小时：不补发，滚动到下次
            if sub.next_sent_at and sub.next_sent_at < stale_cutoff:
                logger.warning(f"[beat] 订阅 {sub.id} 到期超 24 小时，跳过并滚动到下次")
                _update_next_sent(db, sub.id)
                continue
            # 已有进行中的生成任务：不重复派发
            active = db.query(TaskRun).filter(
                TaskRun.task_type == "report",
                TaskRun.ref_id == sub.id,
                TaskRun.status == "running",
                TaskRun.created_at >= running_cutoff,
            ).first()
            if active:
                logger.info(f"[beat] 订阅 {sub.id} 存在进行中任务(task_run#{active.id})，跳过")
                continue
            logger.info(f"[beat] 派发订阅 {sub.id} (next_sent_at={sub.next_sent_at})")
            generate_report.delay(sub.id)
            dispatched += 1

        if not dispatched:
            logger.debug("[beat] 无到期订阅")
    except Exception as e:
        logger.error(f"[beat] 检查失败: {e}")
    finally:
        db.close()


@celery_app.task(name="ingest_news_pool")
def ingest_news_pool():
    """信息池常驻抓取入库（每 30 分钟；生产模式下由 beat 调度，替代本地调度器）"""
    from app.database import SessionLocal
    from app.services.pool import ingest_sources

    db = SessionLocal()
    try:
        stats = ingest_sources(db)
        logger.info(f"[信息池] 入库完成: {stats}")
    except Exception as e:
        logger.error(f"[信息池] 入库失败: {e}")
    finally:
        db.close()


@celery_app.task(name="watchdog")
def watchdog():
    """生产看门狗：每 15 分钟自愈孤儿任务 + 统计告警"""
    from app.database import SessionLocal
    from app.models.task_run import TaskRun
    from app.models.report import Report

    db = SessionLocal()
    try:
        stale_before = datetime.utcnow() - timedelta(minutes=15)
        n1 = db.query(TaskRun).filter(
            TaskRun.status == "running", TaskRun.created_at < stale_before
        ).update({"status": "failed", "error": "服务重启中断"}, synchronize_session=False)
        n2 = db.query(Report).filter(
            Report.status.in_(["fetching", "analyzing"]), Report.created_at < stale_before
        ).update({"status": "failed", "error_message": "服务重启中断，请重新触发"}, synchronize_session=False)
        db.commit()
        if n1 or n2:
            logger.warning(f"[watchdog] 标记孤儿任务 {n1} 个、中断报告 {n2} 份")

        # 统计最近 24h 失败数（供日志与外部监控参考）
        fail_24h = db.query(Report).filter(
            Report.status == "failed",
            Report.created_at >= datetime.utcnow() - timedelta(hours=24),
        ).count()
        if fail_24h:
            logger.warning(f"[watchdog] 最近 24 小时失败报告 {fail_24h} 份")
    except Exception as e:
        logger.error(f"[watchdog] 执行失败: {e}")
    finally:
        db.close()
