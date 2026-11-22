"""
Task runner: try Celery, fallback to background thread when unavailable."""

from __future__ import annotations
from loguru import logger
import threading
from app.config import get_settings

settings = get_settings()


def _run_in_thread(task_func, *args, **kwargs):
    """Run a task function in a background thread."""
    def _wrapper():
        try:
            task_func.run(*args, **kwargs)
        except Exception as e:
            logger.error(f"[BG] Task {task_func.name} failed: {e}")
    t = threading.Thread(target=_wrapper, daemon=True)
    t.start()
    return t


def try_celery_delay(task_func, *args, **kwargs):
    """
    Try to run via Celery async. If Celery/Redis unavailable, run in background thread.
    """
    if settings.use_sqlite:
        logger.warning(f"[DEV] Celery skipped, running {task_func.name} in background thread")
        _run_in_thread(task_func, *args, **kwargs)
        return None

    try:
        return task_func.apply_async(args=args, kwargs=kwargs, argsrepr='<redacted>', kwargsrepr='<redacted>')
    except Exception as e:
        logger.error(f"Celery dispatch failed: {type(e).__name__}")
        from fastapi import HTTPException
        raise HTTPException(503, "发送队列暂不可用，尚未提交，请稍后重试") from None
