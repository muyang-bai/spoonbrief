"""
任务运行记录：报告生成全生命周期持久化（P3 可靠性）
"""
from __future__ import annotations
from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime, Text

from app.database import Base


class TaskRun(Base):
    __tablename__ = "task_runs"

    id = Column(Integer, primary_key=True, index=True)
    task_type = Column(String(30), default="report", index=True)   # report
    ref_id = Column(Integer, index=True)                           # subscription_id
    status = Column(String(20), default="running", index=True)     # running / done / failed
    stage = Column(String(20), default="fetching")                 # fetching / analyzing / sending
    attempts = Column(Integer, default=1)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


def touch_task(db, task_id, stage=None, status=None, error=None):
    """更新任务阶段/状态"""
    run = db.query(TaskRun).get(task_id)
    if run:
        if stage:
            run.stage = stage
        if status:
            run.status = status
        if error is not None:
            run.error = error
        run.updated_at = datetime.utcnow()
        db.commit()
