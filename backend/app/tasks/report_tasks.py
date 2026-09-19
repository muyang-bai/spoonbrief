"""
报告生成任务：拉取新闻 → AI 分析 → 发送邮件
"""

from __future__ import annotations
import asyncio
import json
from datetime import datetime, timezone
from loguru import logger
from croniter import croniter
from dateutil import tz

from app.tasks.celery_app import celery_app
from app.config import get_settings

settings = get_settings()


@celery_app.task(name="generate_report", bind=True, max_retries=2)
def generate_report(self, subscription_id: int):
    """生成报告：拉取新闻 → AI 分析 → 发送邮件"""
    from app.database import SessionLocal
    from app.models.subscription import Subscription, TimeWindow
    from app.models.user import User
    from app.models.email_address import EmailAddress
    from app.models.news_source import NewsSource
    from app.models.report import Report, ReportStatus
    from app.models.compliance_text import ComplianceText
    from app.services.news_fetcher import get_news_fetcher
    from app.services.ai_analyzer import get_analyzer, _clean_ai_output
    from app.services.email_sender import send_email_sync
    from app.services.email_template import render_email
    from app.models.keyword_stat import KeywordStat

    db = SessionLocal()
    task_id = None
    try:
        sub = db.query(Subscription).get(subscription_id)
        if not sub or not sub.is_active:
            logger.warning(f"订阅 {subscription_id} 不存在或已禁用")
            return

        user = db.query(User).get(sub.user_id)
        if not user:
            return

        # 最终防重：10 分钟内已有成功发送的报告则跳过（防崩溃后调度重复触发）
        from datetime import timedelta as _td
        recent_sent = db.query(Report).filter(
            Report.subscription_id == subscription_id,
            Report.status == ReportStatus.SENT.value,
            Report.created_at >= datetime.utcnow() - _td(minutes=10),
        ).first()
        if recent_sent:
            logger.warning(f"订阅 {subscription_id} 10 分钟内已发送过（报告#{recent_sent.id}），跳过重复生成")
            return

        # ── 额度统一计费（手动/定时同规则，均可预期）──
        from app.deps import ensure_quota_available, consume_api_quota
        if not ensure_quota_available(user, db):
            logger.warning(f"订阅 {subscription_id} 用户 {user.id} 本月额度已用完，跳过并通知")
            _skip_with_notice(db, subscription_id, user, sub,
                              "本月额度已用完（可在「我的画像」查看额度与重置时间，或联系管理员调整）")
            return

        # ── 订阅级月度上限（防"忘记关闭订阅"持续消耗）──
        if sub.monthly_quota and sub.monthly_quota > 0:
            month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            used_this_month = db.query(Report).filter(
                Report.subscription_id == subscription_id,
                Report.status == ReportStatus.SENT.value,
                Report.created_at >= month_start,
            ).count()
            if used_this_month >= sub.monthly_quota:
                logger.warning(f"订阅 {subscription_id} 本月已达上限 {sub.monthly_quota} 份，跳过并通知")
                _skip_with_notice(db, subscription_id, user, sub,
                                  f"本月推送已达订阅上限（{sub.monthly_quota} 份），已自动跳过本次。可在订阅编辑中调整上限或取消限制")
                return

        # P3：任务持久化（阶段/状态全程落库，支持启动自愈）
        from app.models.task_run import TaskRun, touch_task
        run = TaskRun(task_type="report", ref_id=subscription_id, status="running", stage="fetching")
        db.add(run)
        db.commit()
        task_id = run.id

        # 创建报告记录（提前设置主题避免"未命名报告"）
        report_name = (sub.name or "").strip() or "热点速报"
        date_str = datetime.now(tz=tz.gettz("Asia/Shanghai")).strftime("%Y-%m-%d %H:%M")
        report = Report(
            user_id=user.id,
            subscription_id=sub.id,
            status=ReportStatus.FETCHING.value,
            subject=f"{report_name} - {date_str}",
        )
        db.add(report)
        db.commit()
        db.refresh(report)

        try:
            # 1. 解析关键词（兼容中英文逗号/分号/顿号/空格分隔；曾因仅按英文逗号切分导致
            #    「苹果手机的折叠屏，苹果Duo」整串变单关键词而零命中——严重 BUG 修复）
            import re as _re
            keywords = [k for k in _re.split(r"[,，;；、\s]+", sub.keywords or "") if k.strip()]
            if not keywords:
                keywords = ["热点"]

            for kw in keywords:
                stat = db.query(KeywordStat).filter(KeywordStat.keyword == kw).first()
                if stat:
                    stat.search_count += 1
                    stat.updated_at = datetime.utcnow()
                else:
                    db.add(KeywordStat(keyword=kw, search_count=1))
            db.commit()

            # 2. 获取新闻（信息池优先：池空则现场抓取一轮入库后再抽取）
            days = TimeWindow(sub.time_window).days
            from app.services.pool import query_pool, ingest_sources, extract_interest_words

            persona_words = extract_interest_words(user.persona_json)
            news_items = query_pool(db, keywords, sub.category_id, days, persona_words=persona_words)
            if not news_items:
                logger.info("信息池为空，现场抓取一轮入库")
                fetch_stats = ingest_sources(db)
                news_items = query_pool(db, keywords, sub.category_id, days, persona_words=persona_words)
            else:
                from app.models.news_item import NewsItem
                fetch_stats = {
                    "sources_used": [r[0] for r in db.query(NewsItem.source_name).distinct().all()],
                    "sources_failed": [],
                    "pool_size": db.query(NewsItem).count(),
                }

            if not news_items:
                sources_names = ", ".join(fetch_stats.get("sources_used", [])) or "无"
                failed_names = ", ".join(fetch_stats.get("sources_failed", [])) or "无"
                report.status = ReportStatus.FAILED.value
                report.error_message = (
                    f"未检索到匹配的热点信息。\n"
                    f"成功信息源: {sources_names}\n"
                    f"失败信息源: {failed_names}\n"
                    f"建议：扩大时间范围或更换关键词后重试"
                )
                db.commit()
                _update_next_sent(db, sub.id)
                return

            # 2.5 用户自定义 RSS 源：抓取并入简报素材（个人源池，置入"与你相关"层）
            custom_items = _fetch_user_sources(db, user.id, days)
            if custom_items:
                # 与公共池按标题去重，避免重复条目
                existing_titles = {i.get("title") for i in news_items}
                custom_items = [c for c in custom_items if c.get("title") not in existing_titles]
                news_items = news_items + custom_items
                news_items.sort(key=lambda x: (x.get("relevance", 0) > 0, x.get("relevance", 0)), reverse=True)

            report.raw_news_json = json.dumps(news_items, ensure_ascii=False)
            report.status = ReportStatus.ANALYZING.value
            db.commit()
            touch_task(db, task_id, stage="analyzing")

            # 3. AI 分析（三阶段 + 输出清洗）
            ai_html = ""
            if sub.ai_analysis:
                analyzer = get_analyzer()
                ai_html = _run_async(analyzer.analyze(news_items, user, db, sub.prompt_template_id, sub.api_key_id, keywords=keywords))
                # Safety: clean output again
                ai_html = _clean_ai_output(ai_html)
            else:
                ai_html = "<p>AI 分析已关闭。</p>"

            # 3.5 [N] 引用 → 原文链接（在分析正文里即可点击溯源）
            ai_html = _linkify_citations(ai_html, news_items)

            report.ai_analysis_html = ai_html

            # 4. 获取收件邮箱
            emails = (
                db.query(EmailAddress)
                .filter(
                    EmailAddress.user_id == user.id,
                    EmailAddress.is_verified == True,
                )
                .all()
            )
            to_emails = [e.email for e in emails[:3]]
            if not to_emails:
                to_emails = [user.email]

            # 5. 获取合规文本
            compliance = {}
            for key in ["icp_record", "privacy_policy", "unsubscribe_notice"]:
                ct = db.query(ComplianceText).filter(ComplianceText.key == key).first()
                compliance[key] = ct.content if ct else ""

            # 生成退订 token
            from app.models.unsubscribe_token import UnsubscribeToken
            unsubscribe_tokens = {}
            for email in to_emails:
                token = UnsubscribeToken.generate()
                record = UnsubscribeToken(
                    token=token,
                    user_id=user.id,
                    subscription_id=sub.id,
                    email=email,
                )
                db.add(record)
                unsubscribe_tokens[email] = token
            db.commit()

            # 6. 渲染邮件并逐收件人发送（每人使用自己的退订链接）
            touch_task(db, task_id, stage="sending")
            subject = f"{report_name} - {date_str}"
            _WINDOW_LABELS = {"today": "今日", "3d": "近 3 天", "7d": "近 7 天", "10d": "近 10 天",
                              "15d": "近 15 天", "20d": "近 20 天", "25d": "近 25 天", "30d": "近 30 天"}
            time_window_label = _WINDOW_LABELS.get(sub.time_window, sub.time_window or "近 7 天")
            # 三层结构分层：相关层（画像/关键词命中）与广度层（各层封顶 15 条，控制邮件篇幅）
            related_items = [i for i in news_items if i.get("relevance", 0) > 0][:15]
            breadth_items = [i for i in news_items if i.get("relevance", 0) <= 0][:15]
            send_results = []
            for email in to_emails:
                token = unsubscribe_tokens.get(email, "")
                unsubscribe_url = f"{settings.app_url}/api/v1/unsubscribe?token={token}" if token else ""

                html_body = render_email(
                    subscription_name=sub.name if sub.name and sub.name.strip() else "热点速报",
                    date_str=date_str,
                    time_window=time_window_label,
                    ai_analysis_html=ai_html,
                    related_items=related_items,
                    breadth_items=breadth_items,
                    unsubscribe_notice=compliance.get("unsubscribe_notice", ""),
                    privacy_policy=compliance.get("privacy_policy", ""),
                    icp_record=compliance.get("icp_record", ""),
                    unsubscribe_url=unsubscribe_url,
                )
                # 发送失败自动重试一次（间隔 5 秒，规避瞬时 SMTP 抖动）
                ok = send_email_sync([email], subject, html_body)
                if not ok:
                    logger.warning(f"邮件发送失败，5 秒后重试一次: {email}")
                    import time as _time
                    _time.sleep(5)
                    ok = send_email_sync([email], subject, html_body)
                send_results.append(ok)

            # 7. 全部收件人发送成功才算成功
            success = bool(send_results) and all(send_results)

            if success:
                report.status = ReportStatus.SENT.value
                report.sent_at = datetime.utcnow()
                report.subject = subject
            else:
                report.status = ReportStatus.FAILED.value
                report.error_message = "邮件发送失败（请检查SMTP配置）"
                _alert_admin_failure(subscription_id, "邮件发送失败（请检查 SMTP 配置）")

            db.commit()
            touch_task(db, task_id, stage="done" if success else "failed",
                       status="done" if success else "failed",
                       error=None if success else report.error_message)

            # 推送成功 → 统一扣除 1 额度（手动与定时同一规则）
            if success:
                consume_api_quota(user, db)

            # 8. 自动清理
            _cleanup_old_reports(db, user.id)

            logger.info(f"报告生成完成 [sub={subscription_id}] status={report.status} subject={subject}")

        except Exception as e:
            logger.error(f"报告生成失败 [sub={subscription_id}]: {e}")
            report.status = ReportStatus.FAILED.value
            report.error_message = str(e)
            db.commit()
            if task_id:
                touch_task(db, task_id, status="failed", error=str(e)[:500])
            _alert_admin_failure(subscription_id, str(e))

        # 推进下次发送时间
        _update_next_sent(db, subscription_id, success=(report.status == ReportStatus.SENT.value))

    finally:
        db.close()


def _fetch_user_sources(db, user_id: int, days: int) -> list:
    """抓取用户自定义 RSS 源（个人源池；失败仅记录不影响主流程）"""
    from datetime import timedelta as _td2
    import feedparser
    import httpx
    from app.models.user_news_source import UserNewsSource

    sources = db.query(UserNewsSource).filter(
        UserNewsSource.user_id == user_id,
        UserNewsSource.is_active == True,
    ).all()
    if not sources:
        return []

    items = []
    since = datetime.utcnow() - _td2(days=days)
    for src in sources:
        try:
            resp = httpx.get(src.url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15, follow_redirects=True)
            feed = feedparser.parse(resp.content)
            for e in feed.entries[:20]:
                published = None
                if getattr(e, "published_parsed", None):
                    published = datetime(*e.published_parsed[:6])
                if published and published < since:
                    continue
                items.append({
                    "title": getattr(e, "title", "") or "(无标题)",
                    "summary": (getattr(e, "summary", "") or "")[:500],
                    "link": getattr(e, "link", "") or "",
                    "source": f"{src.name}",
                    "category": src.category or "自定义",
                    "published": published.isoformat() if published else None,
                    "credibility": 4,          # 自定义源默认 4，评分仅供参考
                    "_matched": True,
                    "_cross_validated": False,
                    "_source_count": 1,
                    "relevance": 6,            # 用户自建源视为与其相关，置入"与你相关"层
                })
            src.last_fetch_at = datetime.utcnow()
            src.last_error = None
            logger.info(f"[自定义源] {src.name} 抓取 {len(feed.entries[:20])} 条")
        except Exception as e:
            src.last_error = str(e)[:200]
            logger.warning(f"[自定义源] {src.name} 抓取失败: {e}")
        db.commit()
    return items


def _linkify_citations(html: str, news_items: list) -> str:
    """把 AI 分析正文中的 [N] 引用替换为对应原始新闻的超链接（可点击溯源）"""
    if not html:
        return html
    for i, it in enumerate(news_items[:12]):
        link = (it.get("link") or "").strip()
        if not link.startswith("http"):
            continue
        marker = f"[{i + 1}]"
        if marker in html:
            html = html.replace(
                marker,
                f'<a href="{link}" target="_blank" rel="noopener" '
                f'style="color:#f97316;text-decoration:underline;">{marker}</a>',
            )
    return html


def _skip_with_notice(db, sub_id: int, user, sub, reason: str):
    """额度/上限拦截：记录一次失败报告 + 邮件通知用户 + 滚动下次发送时间"""
    from app.models.report import Report, ReportStatus
    report = Report(
        user_id=user.id,
        subscription_id=sub_id,
        status=ReportStatus.FAILED.value,
        subject=f"{sub.name} - 未推送（额度）",
        error_message=reason,
    )
    db.add(report)
    db.commit()
    try:
        from app.services.email_sender import send_email_sync
        html = (
            '<div style="font-family:sans-serif;padding:14px;font-size:14px;line-height:1.9;">'
            f"<p style=\"margin:0 0 6px;\">您的订阅「{sub.name}」本次未能推送。</p>"
            f"<p style=\"margin:0 0 6px;color:#555;\">原因：{reason}</p>"
            '<p style="margin:0;color:#999;font-size:12.5px;">此通知由 一勺热点 自动发送，请勿回复。</p>'
            "</div>"
        )
        send_email_sync([user.email], f"[一勺热点] 订阅「{sub.name}」未推送通知", html)
        logger.info(f"[额度拦截] 已通知用户 {user.email}: {reason}")
    except Exception as e:
        logger.error(f"[额度拦截] 通知邮件发送失败: {e}")
    _update_next_sent(db, sub_id)


def _alert_admin_failure(sub_id: int, reason: str):
    """报告生成/发送失败时给管理员发送告警邮件（SMTP 未配置则仅记录日志）"""
    from app.services.email_sender import send_email_sync
    try:
        if not settings.smtp_host or not settings.admin_email:
            logger.warning(f"[告警] 报告生成失败 sub={sub_id}: {reason}")
            return
        html = (
            '<div style="font-family:sans-serif;padding:16px;font-size:14px;line-height:1.9;">'
            '<h3 style="color:#c0392b;margin:0 0 10px;">一勺热点 定时任务告警</h3>'
            f"<p style=\"margin:4px 0;\">订阅 ID: <b>{sub_id}</b></p>"
            f"<p style=\"margin:4px 0;\">原因: {reason}</p>"
            f"<p style=\"margin:4px 0;\">时间(UTC): {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}</p>"
            '<p style="margin:10px 0 0;color:#666;">请登录管理后台检查订阅与 SMTP/AI 配置。</p>'
            "</div>"
        )
        send_email_sync([settings.admin_email], f"[一勺热点 告警] 报告生成失败 sub={sub_id}", html)
        logger.info(f"[告警] 已发送失败告警邮件 -> {settings.admin_email}")
    except Exception as e:
        logger.error(f"[告警] 告警邮件发送失败: {e}")


def _update_next_sent(db, sub_id: int, success: bool = False):
    """根据 cron 表达式计算下次发送时间"""
    from app.models.subscription import Subscription

    sub = db.query(Subscription).get(sub_id)
    if not sub:
        return

    tz_obj = tz.gettz(sub.timezone or "Asia/Shanghai")
    now = datetime.now(tz=tz_obj)
    try:
        cron = croniter(sub.cron_expr, now)
        next_time = cron.get_next(datetime)
    except Exception as e:
        # cron 无效时的兜底（正常流程已被 API 校验拦截，此处仅防御历史脏数据）
        logger.warning(f"订阅 {sub.id} 的 cron 表达式无效({sub.cron_expr}: {e})，回退到次日 09:00")
        next_time = now.replace(hour=9, minute=0, second=0, microsecond=0)
        if next_time <= now:
            from datetime import timedelta
            next_time = next_time + timedelta(days=1)

    if success:
        sub.last_sent_at = datetime.utcnow()
    sub.next_sent_at = next_time.astimezone(timezone.utc).replace(tzinfo=None)
    db.commit()
    logger.info(f"订阅 {sub.id} 下次发送: {next_time}")


def _cleanup_old_reports(db, user_id: int):
    """自动清理：每个用户最多保留 100 条报告"""
    from app.models.report import Report
    MAX = 100
    old_ids = db.query(Report.id).filter(
        Report.user_id == user_id
    ).order_by(Report.created_at.desc()).offset(MAX).all()
    ids = [r[0] for r in old_ids]
    if ids:
        db.query(Report).filter(Report.id.in_(ids)).delete(synchronize_session=False)
        db.commit()
        logger.info(f"用户 {user_id} 自动清理 {len(ids)} 条旧报告")


def _run_async(coro):
    """安全运行异步协程"""
    import concurrent.futures
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop is not None and loop.is_running():
        with concurrent.futures.ThreadPoolExecutor() as pool:
            future = pool.submit(lambda: asyncio.new_event_loop().run_until_complete(coro))
            return future.result(timeout=120)
    else:
        return asyncio.new_event_loop().run_until_complete(coro)