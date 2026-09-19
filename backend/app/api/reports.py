"""
报告路由
"""

from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.deps import get_current_user
from app.models.user import User
from app.models.report import Report

router = APIRouter(prefix="/reports", tags=["报告"])

MAX_REPORTS = 100

def _iso(dt):
    """naive(UTC) datetime → 带时区的 ISO，前端才能正确显示北京时间"""
    from datetime import timezone
    return dt.replace(tzinfo=timezone.utc).isoformat() if dt else None


@router.get("/")
async def list_reports(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    reports = db.query(Report).filter(Report.user_id == user.id).order_by(Report.created_at.desc()).limit(MAX_REPORTS).all()
    return [
        {
            "id": r.id,
            "subscription_id": r.subscription_id,
            "subject": r.subject,
            "status": r.status,
            "ai_analysis_html": r.ai_analysis_html[:500] if r.ai_analysis_html else None,
            "has_content": bool(r.ai_analysis_html and r.ai_analysis_html.strip()),
            "created_at": _iso(r.created_at),
            "sent_at": _iso(r.sent_at),
            "error_message": r.error_message,
        }
        for r in reports
    ]


@router.get("/{report_id}")
async def get_report(report_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    report = db.query(Report).filter(Report.id == report_id, Report.user_id == user.id).first()
    if not report:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "报告不存在，可能已被删除")
    return {
        "id": report.id,
        "subscription_id": report.subscription_id,
        "subject": report.subject,
        "status": report.status,
        "ai_analysis_html": report.ai_analysis_html,
        "raw_news_json": report.raw_news_json,
        "created_at": _iso(report.created_at),
        "sent_at": _iso(report.sent_at),
        "error_message": report.error_message,
    }


@router.delete("/{report_id}")
async def delete_report(report_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    report = db.query(Report).filter(Report.id == report_id, Report.user_id == user.id).first()
    if not report:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "报告不存在，可能已被删除")
    db.delete(report)
    db.commit()
    return {"message": "报告已删除"}


@router.post("/cleanup")
async def cleanup_reports(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """清理旧报告：只保留最近100条"""
    report_ids = db.query(Report.id).filter(Report.user_id == user.id).order_by(Report.created_at.desc()).offset(MAX_REPORTS).all()
    ids = [r[0] for r in report_ids]
    if ids:
        db.query(Report).filter(Report.id.in_(ids)).delete(synchronize_session=False)
        db.commit()
        return {"message": f"已清理 {len(ids)} 条旧报告，当前保留最近 {MAX_REPORTS} 条"}
    return {"message": "无需清理，报告数未超过上限"}