"""
本地定时调度器：在进程内运行，使用文件锁防止多 worker 重复
"""

from __future__ import annotations
import asyncio
import os
import tempfile
from datetime import datetime
from loguru import logger

try:
    import fcntl  # POSIX only
except ImportError:  # Windows 无 fcntl
    fcntl = None

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger


_scheduler: AsyncIOScheduler = None
_running_subscriptions: set = set()
_lock_file = None

LOCK_PATH = os.path.join(tempfile.gettempdir(), "hotmailbrief_scheduler.lock")


def _acquire_lock() -> bool:
    """获取文件锁，防止多 worker 重复启动调度器"""
    global _lock_file
    if fcntl is None:
        # Windows：无 fcntl，开发模式单 worker 直接放行
        return True
    try:
        _lock_file = open(LOCK_PATH, "w")
        fcntl.flock(_lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        _lock_file.write(str(os.getpid()))
        _lock_file.flush()
        return True
    except (IOError, OSError):
        if _lock_file:
            _lock_file.close()
            _lock_file = None
        return False


def start_local_scheduler():
    """启动本地调度器，每60秒检查到期订阅"""
    global _scheduler

    if _scheduler is not None:
        return

    # Try to acquire file lock (only one worker gets to run the scheduler)
    if not _acquire_lock():
        logger.info("调度器锁已被其他 worker 持有，跳过启动")
        return

    _scheduler = AsyncIOScheduler()
    _scheduler.add_job(
        _check_due_subscriptions,
        IntervalTrigger(seconds=60),
        id="local_check_due",
        replace_existing=True,
    )
    _scheduler.add_job(
        _ingest_news_pool,
        IntervalTrigger(minutes=30),
        id="news_pool_ingest",
        replace_existing=True,
        next_run_time=None,  # 启动后由下方手动触发首轮
    )
    _scheduler.start()
    logger.info(f"本地定时调度器已启动（PID={os.getpid()}，每60秒检查到期订阅，每30分钟信息池入库）")

    # 启动时立即入池一轮 + 自愈孤儿任务（后台线程）
    import threading
    threading.Thread(target=_ingest_news_pool, daemon=True).start()
    threading.Thread(target=recover_stale_runs, daemon=True).start()


def _ingest_news_pool():
    """信息池常驻抓取入库（后台线程）"""
    try:
        from app.database import SessionLocal
        from app.services.pool import ingest_sources
        db = SessionLocal()
        try:
            stats = ingest_sources(db)
            logger.info(f"[信息池] 入库完成: {stats}")
        finally:
            db.close()
    except Exception as e:
        logger.error(f"[信息池] 入库失败: {e}")


def stop_local_scheduler():
    global _scheduler, _lock_file
    if _scheduler:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        logger.info("本地定时调度器已停止")
    if _lock_file:
        try:
            fcntl.flock(_lock_file, fcntl.LOCK_UN)
            _lock_file.close()
        except Exception:
            pass
        _lock_file = None


async def _check_due_subscriptions():
    """检查所有到期订阅并触发报告生成（过期超 24h 的窗口不补发，直接滚动到下次）"""
    from app.database import SessionLocal
    from app.models.subscription import Subscription
    from datetime import timedelta

    db = SessionLocal()
    try:
        now = datetime.utcnow()
        due_subs = db.query(Subscription).filter(
            Subscription.is_active == True,
            Subscription.next_sent_at <= now,
        ).all()

        for sub in due_subs:
            # 重启后避免补发过期窗口：超过 24 小时的到期直接滚动，不发送
            if sub.next_sent_at and sub.next_sent_at < now - timedelta(hours=24):
                logger.warning(f"[调度器] 订阅 {sub.id} 到期已超 24 小时，跳过并滚动到下次")
                from app.tasks.report_tasks import _update_next_sent
                _update_next_sent(db, sub.id)
                continue
            logger.info(f"[调度器] 触发订阅 {sub.id} (next_sent_at={sub.next_sent_at})")
            await _dispatch_report(sub.id)
        if not due_subs:
            logger.debug("[调度器] 无到期订阅")
    except Exception as e:
        logger.error(f"[调度器] 检查失败: {e}")
    finally:
        db.close()


def recover_stale_runs():
    """启动自愈：孤儿任务/中断报告标记失败（运行中超过 15 分钟视为中断）"""
    from app.database import SessionLocal
    from app.models.task_run import TaskRun
    from app.models.report import Report
    from datetime import timedelta

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
            logger.warning(f"[自愈] 标记孤儿任务 {n1} 个、中断报告 {n2} 份")
    except Exception as e:
        logger.error(f"[自愈] 执行失败: {e}")
    finally:
        db.close()


async def _dispatch_report(subscription_id: int):
    """派发报告生成（线程池隔离，不阻塞事件循环）"""
    global _running_subscriptions
    if subscription_id in _running_subscriptions:
        logger.warning(f"[调度器] 订阅 {subscription_id} 仍在处理中，跳过重复派发")
        return
    _running_subscriptions.add(subscription_id)
    try:
        from app.tasks.report_tasks import generate_report
        await asyncio.to_thread(generate_report.run, subscription_id)
        logger.info(f"[调度器] 订阅 {subscription_id} 报告生成完成")
    except Exception as e:
        logger.error(f"[调度器] 订阅 {subscription_id} 报告生成失败: {e}")
    finally:
        _running_subscriptions.discard(subscription_id)