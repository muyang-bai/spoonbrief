"""
报告路由
"""

from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session

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


def _feedback_page(title: str, body: str, status_code: int = 200):
    from fastapi.responses import HTMLResponse
    from app.api.unsubscribe import _page
    return HTMLResponse(_page(title, body), status_code=status_code)


_FB_INVALID = "<h2>反馈链接已失效</h2><p>这个链接不完整或已过期。可以登录控制台在「历史报告」里查看这期简报。</p>"


@router.get("/feedback")
async def feedback_page(rid: int, v: str = "up", s: str | None = None, reason: str | None = None, db: Session = Depends(get_db)):
    """邮件底部「有用 / 没用」：GET 只展示页面，由页面脚本 POST 真正记录（防预取、防刷）"""
    import html as _h
    from app.services import feedback_link

    value = "up" if str(v).lower() in ("up", "1", "good", "yes") else "down"
    report = db.query(Report).filter(Report.id == rid).first()
    if not report or not feedback_link.is_valid(report, s):
        return _feedback_page("反馈链接已失效", _FB_INVALID, 404)

    q = f"rid={report.id}&v={value}" + (f"&s={_h.escape(s)}" if s else "")
    label = "有用" if value == "up" else "没用"
    # 「没用」先问原因：归因决定下一期怎么改，不归因也允许直接记录
    if value == "down" and not reason:
        options = [("direction", "方向不相关"), ("shallow", "太浅，没增量"),
                   ("stale", "太旧或重复"), ("evidence", "依据不足或有误"), ("length", "太长或太频繁")]
        buttons = "".join(
            f'<form method="post" action="/api/v1/reports/feedback?{q}&reason={key}" style="display:inline-block;margin:8px 8px 0 0">'
            f'<button class="btn" type="submit">{text}</button></form>'
            for key, text in options
        )
        body = (
            "<h2>这期哪里不合适？</h2>"
            "<p class=\"muted\">选一个原因，下一期会据此调整；不选也能记录。</p>"
            + buttons +
            f'<form method="post" action="/api/v1/reports/feedback?{q}" style="margin-top:18px">'
            '<button class="btn" type="submit">跳过归因，直接记「没用」</button></form>'
        )
        return _feedback_page("读后反馈", body)
    body = (
        f"<h2 id=\"t\">正在记录：{label}</h2>"
        "<p id=\"m\" class=\"muted\">稍等一下…</p>"
        f'<form id="f" method="post" action="/api/v1/reports/feedback?{q}">'
        f'<noscript><button class="btn" type="submit">确认：这期{label}</button></noscript></form>'
        "<script>document.getElementById('f').submit()</script>"
    )
    return _feedback_page("读后反馈", body)


@router.post("/feedback")
async def submit_feedback(rid: int, v: str = "up", s: str | None = None, reason: str | None = None,
                          db: Session = Depends(get_db)):
    """记录读后反馈：签名校验 + 每份报告只留一条（重复点击改为更新）+ IP 限频"""
    from datetime import datetime as _dt
    from app.models.report_feedback import ReportFeedback
    from app.services import feedback_link

    # 限频按报告计：线上请求经 nginx → serve_frontend 转发，到这里的来源 IP 基本都是同一个内网地址，
    # 按 IP 限会误伤所有用户；签名保证了无法跨报告刷，所以按 rid 限即可
    if not feedback_link.allow(f"rid:{rid}"):
        return _feedback_page("操作太频繁", "<h2>操作太频繁</h2><p>请过几分钟再试。</p>", 429)

    value = "up" if str(v).lower() in ("up", "1", "good", "yes") else "down"
    report = db.query(Report).filter(Report.id == rid).first()
    if not report or not feedback_link.is_valid(report, s):
        return _feedback_page("反馈链接已失效", _FB_INVALID, 404)

    row = (db.query(ReportFeedback)
           .filter(ReportFeedback.report_id == report.id)
           .order_by(ReportFeedback.id.desc()).first())
    reason_value = (reason or "").strip()[:32] or None
    if row:
        row.value = value
        row.created_at = _dt.utcnow()
        row.reason = reason_value
    else:
        db.add(ReportFeedback(report_id=report.id, user_id=report.user_id,
                              subscription_id=report.subscription_id, value=value,
                              reason=reason_value))
    db.commit()

    title = "谢谢反馈：这期对你有用" if value == "up" else "收到：下期我们调整选材"
    body = (f"<h2>{title}</h2><p>已记录。每期只记一次，改主意的话点另一个按钮就会更新。</p>"
            "<p class=\"muted\">反馈只用于调整下一期的选材角度。</p>")
    return _feedback_page("读后反馈", body)


@router.get("/{report_id}/email-html")
async def report_email_html(report_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """网页端「查看」= 复刻该封推送邮件的版式（与邮件共用同一套模板渲染）"""
    import json as _json
    from fastapi.responses import HTMLResponse

    from app.services.email_template import render_email
    from app.models.subscription import Subscription

    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="报告不存在")
    if report.user_id != user.id and not getattr(user, "is_admin", False):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权查看")

    display = _json.loads(report.display_json or "{}")
    decision = _json.loads(report.decision_json) if report.decision_json else None
    related = display.get("related") or []
    breadth = display.get("breadth") or []
    novelty = display.get("novelty") or {}
    digest_rows = display.get("digest_rows") or []
    progress_items = display.get("progress") or []
    if not related and not breadth:  # 兼容未存展示条目的历史报告
        related = _json.loads(report.raw_news_json or "[]")[:12]

    from app.utils import compliance as _compliance
    from app.services.spoonbrief_digest import clean_citations
    from app.config import get_settings as _gs
    compliance = _compliance.load(db)

    sub = db.query(Subscription).filter(Subscription.id == report.subscription_id).first()
    _WINDOW_LABELS = {"today": "今日", "3d": "近 3 天", "7d": "近 7 天", "10d": "近 10 天",
                      "15d": "近 15 天", "20d": "近 20 天", "25d": "近 25 天", "30d": "近 30 天"}
    window = _WINDOW_LABELS.get(getattr(sub, "time_window", "") or "", "近 7 天")

    stamp = report.sent_at or report.created_at
    date_str = stamp.strftime("%Y年%m月%d日") if stamp else ""
    srcs = {(i.get("source") or "").strip() for i in (related + breadth) if (i.get("source") or "").strip()}
    stats_line = f"入选 {len(related) + len(breadth)} 条 · 来源 {len(srcs)} 家"

    html = render_email(
        subscription_name=(getattr(sub, "name", "") or "热点速报"),
        date_str=date_str,
        time_window=window,
        ai_analysis_html=clean_citations(report.ai_analysis_html or "", _json.loads(report.raw_news_json or "[]")[:20]),
        related_items=related,
        breadth_items=breadth,
        unsubscribe_notice=compliance.get("unsubscribe_notice", ""),
        privacy_policy=compliance.get("privacy_policy", ""),
        icp_record=compliance.get("icp_record", ""),
        unsubscribe_url="",
        decision=decision,
        stats_line=stats_line,
        novelty=novelty,
        progress_items=progress_items,
        digest_rows=digest_rows,
        site_url=_gs().app_url,
    )
    return HTMLResponse(html)


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




@router.post("/batch-delete")
async def batch_delete_reports(request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """批量删除报告（仅限本人，单次最多 500 条）"""
    try:
        body = await request.json()
    except Exception:
        body = {}
    raw = body.get("ids") if isinstance(body, dict) else None
    ids = []
    for x in (raw or []):
        try:
            ids.append(int(x))
        except (TypeError, ValueError):
            continue
    ids = ids[:500]
    if not ids:
        return {"deleted": 0, "message": "未选择报告"}
    n = (db.query(Report)
         .filter(Report.user_id == user.id, Report.id.in_(ids))
         .delete(synchronize_session=False))
    db.commit()
    return {"deleted": int(n), "message": f"已删除 {int(n)} 份报告"}

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