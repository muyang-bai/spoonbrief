"""
邮件 HTML 模板渲染（Jinja2）
主题与网站一致：橙琥珀渐变。
手机邮箱阅读优化（QQ 邮箱 App 实测结论）：
- 纯 div 结构、无任何 <table>、无固定宽度、无 meta viewport、无 text-size-adjust
  —— 这四者是 QQ 邮箱 App 把页面按"桌面宽度"整体缩小显示的诱因；
  实测可读版（字号测试邮件#2）正是纯 div 结构。
- 样式全部内联（QQ 邮箱会剥离 <style>），AI 内容由 _inline_ai_styles 注入内联样式。
- 字号定档：标题 20-22px / 正文 18px / 元信息 16px。
- 风格统一：不使用 emoji 装饰，章节以左侧色条区分（橙=与你相关 / 琥珀=今日要闻）。
"""

from __future__ import annotations
from jinja2 import Template
from bs4 import BeautifulSoup

EMAIL_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
</head>
<body style="margin:0;padding:0;background:#f9fafb;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,'PingFang SC','Microsoft YaHei',sans-serif;">

  <!-- Header -->
  <div style="background:linear-gradient(135deg,#f97316,#f59e0b,#ea580c);padding:20px 14px;text-align:center;">
    <h1 style="margin:0;color:#fff;font-size:22px;font-weight:800;">一勺热点</h1>
    <p style="margin:8px 0 0;color:rgba(255,255,255,0.92);font-size:17px;">{{ subscription_name }}</p>
  </div>

  <!-- Body -->
  <div style="background:#ffffff;padding:14px 14px 16px;">

    <!-- Date -->
    <p style="margin:0 0 12px;color:#9ca3af;font-size:16px;">{{ date_str }} &nbsp;|&nbsp; 时间范围: {{ time_window }}</p>

    <!-- AI Analysis -->
    <div style="border-left:4px solid #f97316;padding-left:10px;margin-bottom:6px;">
      <h2 style="margin:0;font-size:20px;color:#1f2937;font-weight:800;">AI 全局分析</h2>
    </div>
    <p style="margin:0 0 12px;font-size:13px;color:#9ca3af;">AI 分析由 DeepSeek 生成 · 内容仅供参考，不构成投资建议</p>
    {{ ai_analysis_html | safe }}

    <!-- News List -->
    {% if related_items %}
    <h2 style="font-size:20px;color:#1f2937;font-weight:800;border-left:4px solid #f97316;padding-left:10px;margin:20px 0 12px;">与你相关</h2>
    {% for news in related_items %}
    <div style="margin-bottom:12px;padding:14px;background:#fff7ed;border:1px solid #fed7aa;border-radius:12px;">
      <p style="margin:0 0 8px;font-weight:700;color:#1f2937;font-size:20px;line-height:1.5;">【{{ loop.index }}】{{ news.title }}</p>
      <p style="margin:0 0 8px;font-size:18px;color:#4b5563;line-height:1.65;">{{ news.summary }}</p>
      <p style="margin:0;font-size:16px;color:#9ca3af;line-height:1.7;">
        来源: {{ news.source }}
        {% if news.link %}| <a href="{{ news.link }}" style="color:#f97316;text-decoration:underline;">原文链接</a>{% endif %}
        {% if news.credibility %}| 可信度 {{ news.credibility }}/10{% endif %}
        {% if news['_cross_validated'] %}| {{ news['_source_count'] }} 源交叉验证{% endif %}
        {% if news.published %}| {{ news.published }}{% endif %}
      </p>
    </div>
    {% endfor %}
    {% endif %}

    {% if breadth_items %}
    <h2 style="font-size:20px;color:#1f2937;font-weight:800;border-left:4px solid #f59e0b;padding-left:10px;margin:20px 0 12px;">今日要闻</h2>
    {% for news in breadth_items %}
    <div style="margin-bottom:12px;padding:14px;background:#f9fafb;border:1px solid #e5e7eb;border-radius:12px;">
      <p style="margin:0 0 8px;font-weight:700;color:#1f2937;font-size:20px;line-height:1.5;">【{{ loop.index + related_items|length }}】{{ news.title }}</p>
      <p style="margin:0 0 8px;font-size:18px;color:#4b5563;line-height:1.65;">{{ news.summary }}</p>
      <p style="margin:0;font-size:16px;color:#9ca3af;line-height:1.7;">
        来源: {{ news.source }}
        {% if news.link %}| <a href="{{ news.link }}" style="color:#f97316;text-decoration:underline;">原文链接</a>{% endif %}
        {% if news.credibility %}| 可信度 {{ news.credibility }}/10{% endif %}
        {% if news['_cross_validated'] %}| {{ news['_source_count'] }} 源交叉验证{% endif %}
        {% if news.published %}| {{ news.published }}{% endif %}
      </p>
    </div>
    {% endfor %}
    {% endif %}
  </div>

  <!-- Footer -->
  <div style="padding:16px 14px;background:#f9fafb;border-top:1px solid #e5e7eb;">
    {% if unsubscribe_url %}
    <p style="margin:0 0 10px;font-size:16px;">
      <a href="{{ unsubscribe_url }}" style="color:#f97316;text-decoration:underline;font-weight:600;">取消订阅此报告</a>
    </p>
    {% endif %}
    <p style="margin:0 0 8px;font-size:16px;color:#9ca3af;line-height:1.7;">{{ unsubscribe_notice }}</p>
    <p style="margin:0;font-size:16px;color:#9ca3af;line-height:1.7;">{{ icp_record }}</p>
  </div>

</body>
</html>
"""

_INLINE_STYLES = {
    "h1": "font-size:20px;color:#1f2937;margin:16px 0 8px;font-weight:800;",
    "h2": "font-size:19px;color:#1f2937;margin:14px 0 8px;font-weight:800;",
    "h3": "font-size:18px;color:#1f2937;margin:14px 0 8px;font-weight:800;",
    "h4": "font-size:17px;color:#1f2937;margin:12px 0 6px;font-weight:700;",
    "p": "font-size:18px;color:#374151;margin:8px 0;line-height:1.8;",
    "li": "font-size:17px;color:#374151;line-height:1.75;margin:4px 0;",
    "ul": "margin:8px 0 8px 22px;padding:0;",
    "ol": "margin:8px 0 8px 22px;padding:0;",
    "a": "color:#f97316;",
    "strong": "color:#1f2937;",
    "em": "color:#4b5563;",
    "table": "border-collapse:collapse;width:100%;margin:10px 0;",
    "td": "border:1px solid #e5e7eb;padding:8px 10px;font-size:16px;text-align:left;",
    "th": "border:1px solid #e5e7eb;padding:8px 10px;font-size:16px;text-align:left;background:#f9fafb;",
}


def _inline_ai_styles(html: str) -> str:
    """把样式内联进 AI 生成的 HTML（QQ 邮箱会剥离 <style>，内联样式才可靠）"""
    if not html or not html.strip():
        return ""
    soup = BeautifulSoup(html, "html.parser")
    for tag, style in _INLINE_STYLES.items():
        for el in soup.find_all(tag):
            if not (el.get("style") or "").strip():
                el["style"] = style
    return str(soup)


def render_email(
    subscription_name: str,
    date_str: str,
    time_window: str,
    ai_analysis_html: str,
    related_items: list,
    breadth_items: list,
    unsubscribe_notice: str,
    privacy_policy: str,
    icp_record: str,
    unsubscribe_url: str = "",
) -> str:
    tpl = Template(EMAIL_TEMPLATE)
    return tpl.render(
        subscription_name=subscription_name,
        date_str=date_str,
        time_window=time_window,
        ai_analysis_html=_inline_ai_styles(ai_analysis_html),
        related_items=related_items,
        breadth_items=breadth_items,
        unsubscribe_notice=unsubscribe_notice,
        privacy_policy=privacy_policy,
        icp_record=icp_record,
        unsubscribe_url=unsubscribe_url,
    )
