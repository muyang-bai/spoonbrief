"""t161 full-content, source-traceable email. No new AI request or tracking.
Table layout/inline CSS, self-hosted structure diagram; all selected cards and
entire t125 sanitized analyst body retained. No web-view replacement/CTA.
"""
from __future__ import annotations
from datetime import datetime,timezone,timedelta
from jinja2 import Template
from markupsafe import Markup
from bs4 import BeautifulSoup
from app.services.spoonbrief_digest import analysis_body
from app.services.source_reference import safe_url,reference_grade
from app.utils import compliance as _cmp


def text(value):
    soup=BeautifulSoup(str(value or ''),'html.parser')
    for node in soup(['script','style','iframe','object','svg','form']):node.decompose()
    return soup.get_text(' ',strip=True)


def published_label(value):
    if not value:return '日期未提供 · 不作为最新消息认定'
    value=str(value).strip()
    try:
        if len(value)==10:
            datetime.strptime(value,'%Y-%m-%d');return value+' · 来源标注日期'
        stamp=datetime.fromisoformat(value.replace('Z','+00:00'))
        if not stamp.tzinfo:stamp=stamp.replace(tzinfo=timezone.utc)
        label=stamp.astimezone(timezone(timedelta(hours=8))).strftime('%Y-%m-%d %H:%M')+' 北京时间'
        if stamp>datetime.now(timezone.utc)+timedelta(minutes=10):label+=' · 日期异常待核'
        return label
    except ValueError:return '日期格式待核 · 不作为最新消息认定'


def _card(item):
    return dict(title=text(item.get('title')) or '标题未提供',summary=text(item.get('summary')),
                source=text(item.get('source')) or '来源未提供',published=published_label(item.get('published')),
                link=safe_url(item.get('link')),grade=reference_grade(item))

EMAIL_TEMPLATE='''<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8"></head>
<body style="margin:0;padding:0;background:#fcfdff;color:#18304a;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI','PingFang SC','Microsoft YaHei',sans-serif;">
<table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="width:100%;border-collapse:collapse;background:#fcfdff;"><tr><td style="padding:12px 8px;">
<table role="presentation" width="100%" cellspacing="0" cellpadding="0" align="center" style="width:100%;max-width:680px;margin:0 auto;border-collapse:collapse;">
<tr><td style="background:#eef5ff;border-top:4px solid #2868ed;padding:22px 20px;border-radius:16px 16px 0 0;">
<p style="margin:0 0 9px;font-size:16px;color:#2868ed;font-weight:700;">一勺热点 · 你的主题简报</p>
<h1 style="margin:0;font-size:23px;line-height:1.5;font-weight:700;">{{ subscription_name }}</h1>
<p style="margin:10px 0 0;color:#627287;font-size:15px;line-height:1.7;">{{ date_text }}</p></td></tr>
<tr><td style="padding:18px 20px;border:1px solid #e0e9f4;background:#ffffff;">
<p style="margin:0 0 8px;font-size:16px;color:#2868ed;font-weight:700;">本期阅读地图</p>
<table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="border-collapse:collapse;"><tr>
<td style="padding:8px;border-right:1px solid #e0e9f4;font-size:16px;line-height:1.7;">入选素材<br><b style="font-size:24px;">{{ cards|length }}</b> 条</td>
<td style="padding:8px;border-right:1px solid #e0e9f4;font-size:16px;line-height:1.7;">来源名称<br><b style="font-size:24px;">{{ source_count }}</b> 个</td>
<td style="padding:8px;font-size:16px;line-height:1.7;">出处已分级<br><b style="font-size:24px;">{{ rated_count }}</b> 条</td></tr></table>
<p style="margin:8px 0 0;font-size:14px;line-height:1.7;color:#627287;">计数来自本期入选条目；来源名称数不是独立事实核验数。</p>
{% if diagram_url %}<img src="{{ diagram_url }}" width="600" alt="阅读结构示意，非新闻照片：先看本期要点，再读分析师全文，最后逐条核对素材与原文。" style="display:block;width:100%;max-width:600px;height:auto;border:0;margin:16px 0 0;">{% endif %}
<p style="margin:8px 0 0;font-size:14px;line-height:1.7;color:#627287;">阅读顺序：要点 → 分析师全文 → 逐条素材与原文。图片被屏蔽不影响完整正文；图示不是新闻实拍。</p></td></tr>
{% if headline or brief %}<tr><td style="padding:20px;background:#eef5ff;border:1px solid #e0e9f4;">
<h2 style="margin:0 0 10px;color:#2868ed;font-size:18px;">本期要点 · {{ guide_label }}</h2>
{% if headline %}<p style="margin:0;font-size:19px;line-height:1.8;font-weight:600;">{{ headline }}</p>{% endif %}
{% for line in brief %}<p style="margin:10px 0 0;font-size:18px;line-height:1.8;">• {{ line }}</p>{% endfor %}</td></tr>{% endif %}
{% if quality_notice %}<tr><td style="padding:16px 20px;background:#f5f8fd;font-size:16px;color:#51657e;line-height:1.8;">阅读边界：{{ quality_notice }}</td></tr>{% endif %}
{% if analysis %}<tr><td style="padding:24px 20px 18px;border:1px solid #e0e9f4;background:#ffffff;">
<p style="margin:0;color:#2868ed;font-size:15px;font-weight:700;">01 / 理解与判断</p><h2 style="margin:7px 0;font-size:20px;line-height:1.6;">分析师全文{% if analyst_name %} · {{ analyst_name }}{% endif %}</h2>
<p style="margin:0 0 16px;font-size:15px;color:#627287;line-height:1.8;">本节是 AI 辅助分析，不是来源原文或已核实结论；请结合下方素材核对，不替代专业判断。</p>{{ analysis }}</td></tr>{% endif %}
{% if actions %}{% if actions %}<tr><td style="padding:24px 20px 8px;"><p style="margin:0;color:#2868ed;font-size:15px;font-weight:700;">01.2 / 今日行动清单</p><h2 style="margin:7px 0;font-size:20px;">今天可以着手的事</h2><p style="margin:0;font-size:15px;line-height:1.8;color:#627287;">按优先级排列，每条都对应下面的素材；没有把握的部分会标注待核对。</p></td></tr>{% for line in actions %}<tr><td style="padding:8px 20px;"><div style="display:block;border:1px solid #dbe7f7;border-radius:12px;background:#f7fbff;padding:12px 14px;"><span style="display:inline-block;width:24px;height:24px;line-height:24px;text-align:center;border-radius:8px;background:#2868ed;color:#fff;font-size:14px;font-weight:800;">{{ loop.index }}</span><span style="margin-left:8px;font-size:17px;line-height:1.8;">{{ line }}</span></div></td></tr>{% endfor %}{% endif %}{% if dims or rating %}<tr><td style="padding:24px 20px 8px;"><p style="margin:0;color:#2868ed;font-size:15px;font-weight:700;">01.4 / 本期影响评级</p><h2 style="margin:7px 0;font-size:20px;">这期对你的影响有多强</h2><p style="margin:0;font-size:14px;line-height:1.8;color:#627287;">影响分 = 对「钱 / 工作 / 学业」的影响强度（1–10），不是新闻热度。</p></td></tr>{% if dims %}<tr><td style="padding:6px 20px 0;">{% for name, score in dims.items() %}<table role="presentation" width="100%" style="border-collapse:collapse;margin:6px 0;"><tr><td style="width:92px;font-size:15px;color:#3d4a5c;">{{ name }}</td><td><div style="background:#e8eefb;height:12px;border-radius:6px;"><div style="width:{{ (score or 0) * 10 }}%;height:12px;border-radius:6px;background:#5b7cff;"></div></div></td><td style="width:52px;text-align:right;font-size:15px;font-weight:700;color:#18304a;">{{ score }}/10</td></tr></table>{% endfor %}</td></tr>{% endif %}{% if rating %}<tr><td style="padding:10px 20px 0;">{% for r in rating %}<div style="border-top:1px solid #edf1f7;padding:10px 0;"><p style="margin:0;font-size:15px;"><b>{{ r.name }}</b> {{ r.count }} 条 · 平均影响 {{ r.avg }}/10{% if r.top %} · 最强：{{ r.top }}（{{ r.top_impact }}/10）{% endif %}</p></div>{% endfor %}</td></tr>{% endif %}{% endif %}{% endif %}
{% if novelty and novelty.mode == "digest" %}<tr><td style="padding:24px 20px 8px;"><p style="margin:0;color:#2868ed;font-size:15px;font-weight:700;">00 / 本周期回顾</p><h2 style="margin:7px 0;font-size:20px;">这段时间跟踪到的事件</h2><p style="margin:0;font-size:15px;line-height:1.8;color:#627287;">没有新的实质进展，以下事件均为已推送过的回顾，按首次出现时间排列。</p></td></tr>{% for d in digest %}<tr><td style="padding:10px 20px;"><div style="border:1px solid #e0e9f4;border-radius:12px;padding:12px 14px;background:#ffffff;"><p style="margin:0;font-size:16px;font-weight:700;color:#1f2937;">{{ d.title }}</p><p style="margin:6px 0 0;font-size:14px;color:#627287;">首次出现：{{ d.first }} · 来源 {{ d.sources }} 家 · 已推送 {{ d.count }} 次</p></div></td></tr>{% endfor %}{% endif %}
{% if novelty and novelty.mode == "digest" %}<tr><td style="padding:18px 20px;background:#f6f9ff;border:1px solid #e0e9f4;border-radius:14px;"><p style="margin:0;color:#2868ed;font-size:15px;font-weight:700;">本期为周期汇总</p><p style="margin:8px 0 0;font-size:15px;line-height:1.8;color:#51657e;">这段时间没有产生值得单独推送的新事实，下面集中回顾已覆盖的事件；有新进展时会恢复正常推送。</p></td></tr>{% endif %}{% if progress %}<tr><td style="padding:24px 20px 8px;"><p style="margin:0;color:#2868ed;font-size:15px;font-weight:700;">01.5 / 事件进展</p><h2 style="margin:7px 0;font-size:20px;">同一件事，这次新在哪</h2><p style="margin:0;font-size:15px;line-height:1.8;color:#627287;">只列出现新来源或新事实的事件；纯转载不重复推送。</p></td></tr>{% for e in progress %}<tr><td style="padding:14px 20px;"><div style="border-left:4px solid #2868ed;padding:10px 14px;background:#ffffff;border:1px solid #e0e9f4;border-radius:12px;"><p style="margin:0 0 6px;font-size:17px;font-weight:700;color:#1f2937;">{{ e.title }}</p><p style="margin:0;font-size:15px;line-height:1.8;color:#51657e;"><b>上次：</b>{{ e.prev }}</p><p style="margin:4px 0 0;font-size:15px;line-height:1.8;color:#51657e;"><b>本次新增：</b>{{ e.delta }}{% if e.sources %}（{{ e.sources }}）{% endif %}</p>{% if e.link %}<p style="margin:8px 0 0;font-size:15px;"><a href="{{ e.link }}" style="color:#2868ed;text-decoration:none;">查看来源原文 →</a></p>{% endif %}</div></td></tr>{% endfor %}{% endif %}<tr><td style="padding:22px 20px 10px;"><p style="margin:0;color:#2868ed;font-size:15px;font-weight:700;">02 / 事实线索与出处</p><h2 style="margin:7px 0;font-size:20px;">逐条素材 · 完整展开</h2><p style="margin:0;font-size:15px;line-height:1.8;color:#627287;">以下为采集到的标题与素材摘要，不冒充原文全文或人工核实报道。分析已在上节分开呈现；没有配图的素材直接展示正文，不留破图占位。</p></td></tr>
{% for n in cards %}<tr><td style="padding:8px 0;"><table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="width:100%;border:1px solid #e0e9f4;border-radius:14px;background:#ffffff;border-collapse:separate;"><tr><td style="padding:20px;">
<p style="margin:0;color:#2868ed;font-size:15px;line-height:1.7;">素材 {{ loop.index }} · {{ n.source }}</p>
<h3 style="margin:8px 0;font-size:20px;line-height:1.6;">{% if n.link %}<a href="{{ n.link }}" rel="noopener noreferrer" style="color:#18304a;text-decoration:none;word-break:break-word;">{{ n.title }}</a>{% else %}{{ n.title }}{% endif %}</h3>
<p style="margin:0;color:#627287;font-size:15px;line-height:1.7;">{{ n.published }}</p>
<p style="margin:12px 0 0;font-size:18px;color:#344a63;line-height:1.85;word-break:break-word;">{{ n.summary or '本条未提供素材摘要，请结合原文核对；不以模型猜测补齐事实。' }}</p>
<p style="margin:15px 0 0;font-size:16px;color:#2868ed;line-height:1.7;">信源参考等级 <span aria-label="{% if n.grade.stars %}{{ n.grade.stars }}/5{% else %}未评级{% endif %}">{{ n.grade.symbol }}</span> · {% if n.grade.stars %}{{ n.grade.stars }}/5 · {% endif %}{{ n.grade.label }}</p>
<p style="margin:5px 0 0;font-size:14px;color:#627287;line-height:1.8;">依据：{{ n.grade.basis }}{% if n.grade.evidence_url %} · <a href="{{ n.grade.evidence_url }}" style="color:#2868ed;">来源类型依据</a>{% endif %}</p>
{% if n.link %}<p style="margin:12px 0 0;font-size:16px;"><a href="{{ n.link }}" rel="noopener noreferrer" style="color:#2868ed;text-decoration:none;">打开来源文章原文 →</a></p>{% else %}<p style="margin:12px 0 0;font-size:14px;color:#627287;">未提供可安全打开的来源链接，暂不生成跳转。</p>{% endif %}
</td></tr></table></td></tr>{% endfor %}
<tr><td style="padding:18px 20px;background:#eef5ff;border:1px solid #e0e9f4;"><h2 style="margin:0 0 8px;font-size:18px;">怎样理解五颗星</h2><p style="margin:0;font-size:15px;line-height:1.9;">5 星：可溯官方技术文档等一手原文；4 星：专业 / 学术原文（预印本不等于同行评审）；3 星：可溯编辑媒体报道；2 星：社区 / 自媒体原帖；1 星：可溯二手聚合线索；缺少依据：未评级。</p><p style="margin:9px 0 0;font-size:15px;line-height:1.8;">只按已核对站点与正文路径识别来源类型，不按媒体自称或旧权重换算。星级不是内容真实概率、权威认证或 AI 正确性保证；不同类型也可能提供有价值信息。</p></td></tr>
{% if feedback_up_url or feedback_down_url %}<tr><td style="padding:22px 20px;background:#ffffff;border:1px solid #e0e9f4;"><h2 style="margin:0 0 12px;font-size:18px;">这期对你有用吗？</h2>
{% if feedback_up_url %}<a href="{{ feedback_up_url }}" style="display:inline-block;padding:10px 20px;border:1px solid #2868ed;border-radius:10px;color:#2868ed;font-size:16px;">有用</a>{% endif %} {% if feedback_down_url %}<a href="{{ feedback_down_url }}" style="display:inline-block;padding:10px 20px;border:1px solid #dce6f4;border-radius:10px;color:#51657e;font-size:16px;">没用</a>{% endif %}
<p style="margin:10px 0 0;font-size:14px;line-height:1.8;color:#627287;">用于记录本期阅读感受；当前不代表系统已自动据此调整下一期，也不会直接改动你的关注设置。</p></td></tr>{% endif %}
<tr><td style="padding:20px 10px;color:#627287;font-size:14px;line-height:1.9;border-top:1px solid #e0e9f4;">
<p style="margin:0;">一勺热点 · AI 辅助阅读，重要事实请回原文核对。</p>{% if unsubscribe_notice %}<p style="margin:8px 0;">{{ unsubscribe_notice }}</p>{% endif %}
<p style="margin:8px 0 0;">{% if unsubscribe_url %}<a href="{{ unsubscribe_url }}" style="color:#51657e;">退订本订阅</a> · {% endif %}{% if unsubscribe_help_url %}<a href="{{ unsubscribe_help_url }}" style="color:#51657e;">退订说明</a> · {% endif %}{% if privacy_url %}<a href="{{ privacy_url }}" style="color:#51657e;">隐私政策</a>{% endif %}{% if icp_record %} · <a href="{{ icp_url }}" style="color:#627287;">{{ icp_record }}</a>{% endif %}</p>
</td></tr></table></td></tr></table></body></html>'''


def render_email(subscription_name,date_str,time_window,ai_analysis_html,related_items,breadth_items,
                 unsubscribe_notice,privacy_policy,icp_record,unsubscribe_url='',decision=None,
                 feedback_up_url='',feedback_down_url='',stats_line='',more_url='',site_url='',
                 novelty=None,progress_items=None,digest_rows=None):
    """Signature preserved; more_url deliberately unused. No formatting length/card cap."""
    decision=dict(decision or {})
    items=list(related_items or [])+list(breadth_items or [])
    # t170: 影响评级用的结构化统计（情绪分布 + 最强条目）
    _by_idx = (decision or {}).get("items_by_idx") or {}
    _dims = (decision or {}).get("dims") or {}
    _titles = [text(x.get("title")) for x in items]
    _sent = {}
    for _i, _d in _by_idx.items():
        try:
            _idx = int(_i)
        except (TypeError, ValueError):
            continue
        _s = _d.get("sentiment") or "中性"
        _imp = _d.get("impact") or 0
        _slot = _sent.setdefault(_s, {"count": 0, "sum": 0, "top": "", "top_impact": 0})
        _slot["count"] += 1
        _slot["sum"] += _imp
        if _imp >= _slot["top_impact"]:
            _slot["top_impact"] = _imp
            _slot["top"] = _titles[_idx - 1] if 0 < _idx <= len(_titles) else ""
    rating = []
    for _s in ("利好", "利空", "中性"):
        _slot = _sent.get(_s)
        if not _slot:
            continue
        rating.append({"name": _s, "count": _slot["count"],
                       "avg": round(_slot["sum"] / _slot["count"]) if _slot["count"] else 0,
                       "top": _slot["top"][:46], "top_impact": _slot["top_impact"]})
    progress=[{'title':text(x.get('title')),'prev':text(x.get('_progress_from')),'delta':text(x.get('_progress_delta')),
               'link':safe_url(x.get('link')),'sources':text('、'.join(x.get('sources') or []))}
              for x in (progress_items or [])]
    cards=[_card(n) for n in items]
    base=safe_url(site_url or '').rstrip('/')
    return Template(EMAIL_TEMPLATE,autoescape=True).render(
        subscription_name=text(subscription_name) or '热点速报',
        date_text=text(f'{date_str} · {time_window}' if time_window else date_str),
        guide_label='从分析正文摘取，完整内容见下方' if decision.get('_guide_from_analysis') else '历史导读',
        headline=text(decision.get('headline')),brief=[text(x) for x in decision.get('brief',[]) if text(x)],
        actions=[text(x) for x in decision.get('actions',[]) if text(x)],
        quality_notice=text(decision.get('_notice')),
        analysis=Markup(analysis_body(ai_analysis_html,items).replace('text-decoration:underline','text-decoration:none')),
        analyst_name=text((decision.get('_quality') or {}).get('template_name')),
        cards=cards,source_count=len({n['source'] for n in cards}),novelty=novelty or {},progress=progress,digest=digest_rows or [],
        dims=_dims,rating=rating,
        rated_count=sum(bool(n['grade']['stars']) for n in cards),
        diagram_url=base+'/assets/t161-reading-guide.png' if base else '',
        feedback_up_url=safe_url(feedback_up_url),feedback_down_url=safe_url(feedback_down_url),
        unsubscribe_notice=text(_cmp.effective('unsubscribe_notice',unsubscribe_notice)),
        unsubscribe_url=safe_url(unsubscribe_url),
        privacy_url=base+_cmp.PRIVACY_PATH if base else '',
        unsubscribe_help_url=base+_cmp.UNSUBSCRIBE_HELP_PATH if base else '',
        icp_record=text(_cmp.effective('icp_record',icp_record)),icp_url=safe_url(_cmp.ICP_URL))
