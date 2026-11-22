"""SpoonBrief 简报正文清洗与精简（t110 · M3）

把 AI 分析正文和新闻条目整理成「结论 + 要点 + 新闻卡」可用的干净文本：
- 去掉 [N] 编号引用、【】括号、<a> 超链接和裸 URL（邮件里不再出现蓝色链接和方括号）
- 引用处改成句末灰色小字信源名，例如「· 新华社」
- 提供按字数截断、可见字数统计等工具，供速览/新闻卡控制篇幅；t125 起分析师正文不截断
"""

from __future__ import annotations

import html as _html
import re
from typing import Iterable

from bs4 import BeautifulSoup

# 「据[1][2]」「见[3]、[4]」「来源：[5]」以及被「」包住的整段引用
_CITE_GROUP = r"(?:\[\s*\d{1,2}\s*\](?:\s*[、,，和及]?\s*\[\s*\d{1,2}\s*\])*)"
_RE_CITE_QUOTED = re.compile(r"「\s*(?:据|见|来源[:：]?)?\s*(" + _CITE_GROUP + r")\s*」")
_RE_CITE_LEAD = re.compile(r"(?:据|见|来源[:：]?)\s*(" + _CITE_GROUP + r")")
_RE_CITE_BARE = re.compile(_CITE_GROUP)
_RE_NUM = re.compile(r"\d{1,2}")
_RE_URL = re.compile(r"(?:https?://|www\.)[^\s<>\"'）)】」，。；]+", re.IGNORECASE)
_RE_LENTICULAR = re.compile(r"【([^【】]{0,80})】")
_RE_EMPTY_QUOTE = re.compile(r"「\s*」|（\s*）|\(\s*\)")
_RE_SPACES = re.compile(r"[ \t\u00a0]{2,}")

SOURCE_MARK_ATTR = "data-sb-src"


def _source_names(nums: Iterable[int], news_items: list) -> list[str]:
    names: list[str] = []
    for n in nums:
        if 1 <= n <= len(news_items):
            src = (news_items[n - 1].get("source") or "").strip()
            if src and src not in names:
                names.append(src)
    return names


def _cite_repl(news_items: list):
    def repl(m: re.Match) -> str:
        nums = [int(x) for x in _RE_NUM.findall(m.group(1) if m.groups() else m.group(0))]
        names = _source_names(nums, news_items)
        if not names:
            return ""
        label = "、".join(names[:2])
        return f'<span {SOURCE_MARK_ATTR}="1"> · {_html.escape(label)}</span>'
    return repl


def clean_citations(html: str, news_items: list | None = None) -> str:
    """AI 正文：[N] → 灰色信源名；去掉 <a>、裸 URL、【】。返回仍是 HTML 片段。"""
    if not html:
        return ""
    items = list(news_items or [])
    # 1) 先拆掉超链接，只保留文字（旧逻辑会生成【标题】链接，这里一并还原成普通文字）
    soup = BeautifulSoup(html, "html.parser")
    for a in soup.find_all("a"):
        a.unwrap()
    text = str(soup)
    # 2) [N] 引用 → 信源名
    repl = _cite_repl(items)
    text = _RE_CITE_QUOTED.sub(repl, text)
    text = _RE_CITE_LEAD.sub(repl, text)
    text = _RE_CITE_BARE.sub(repl, text)
    # 3) 旧版「据【标题】」引用：去掉整段「据…」；其余【】只去括号保留文字
    text = re.sub(r"「\s*据\s*【[^【】]{0,80}】\s*」", "", text)
    text = _RE_LENTICULAR.sub(lambda m: m.group(1), text)
    # 4) 裸 URL
    text = _RE_URL.sub("", text)
    text = _RE_EMPTY_QUOTE.sub("", text)
    text = _RE_SPACES.sub(" ", text)
    return text


def plain_text(value: str) -> str:
    """HTML/文本 → 纯文本（去 URL、[N]、【】）。"""
    if not value:
        return ""
    s = BeautifulSoup(str(value), "html.parser").get_text(" ")
    s = _RE_CITE_BARE.sub("", s)
    s = _RE_LENTICULAR.sub(lambda m: m.group(1), s)
    s = _RE_URL.sub("", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def clip(value: str, limit: int) -> str:
    s = plain_text(value)
    if len(s) <= limit:
        return s
    cut = s[: max(0, limit - 1)].rstrip("，,、；;：: ")
    return cut + "…"


def ai_points(html: str, news_items: list | None = None, max_points: int = 4, limit: int = 56) -> list[dict]:
    """从 AI 正文里提炼要点：按小标题分组，每组取前 2 条 li / 句子。

    返回 [{"label": "机会", "text": "…", "source": "新华社"}]，label 可能为空。
    """
    if not html:
        return []
    cleaned = clean_citations(html, news_items)
    soup = BeautifulSoup(cleaned, "html.parser")
    points: list[dict] = []
    label = ""
    per_label: dict[str, int] = {}

    def take(node, lab):
        src_nodes = node.find_all(attrs={SOURCE_MARK_ATTR: True}) if hasattr(node, "find_all") else []
        src = ""
        if src_nodes:
            src = src_nodes[0].get_text().replace("·", "").strip()
            for s in src_nodes:
                s.decompose()
        txt = clip(node.get_text(" ") if hasattr(node, "get_text") else str(node), limit)
        if len(txt) < 6:
            return
        if per_label.get(lab, 0) >= 2:
            return
        per_label[lab] = per_label.get(lab, 0) + 1
        points.append({"label": lab, "text": txt, "source": src})

    for el in soup.find_all(["h1", "h2", "h3", "h4", "h5", "li", "p"]):
        if len(points) >= max_points:
            break
        if el.name in ("h1", "h2", "h3", "h4", "h5"):
            label = clip(re.sub(r"^[一二三四五六七八九十\d]+[、.．]\s*", "", el.get_text(" ")), 8)
            continue
        if el.name == "p" and el.find_parent("li"):
            continue
        if el.name == "p" and el.find("strong") and len(el.get_text(strip=True)) > limit:
            # 长段落：只取加粗的论点句
            strong = el.find("strong")
            take(strong, label)
            continue
        take(el, label)
    return points


def visible_length(html: str) -> int:
    """邮件可见字数（去空白），用于统计正文长度（不是删减分析的配额）。"""
    soup = BeautifulSoup(html or "", "html.parser")
    for t in soup(["style", "script", "head"]):
        t.decompose()
    return len(re.sub(r"\s+", "", soup.get_text()))


def analysis_body(value: str, news_items: list | None = None) -> str:
    """保留模板分析师全部文字/章节；去掉不安全标签、属性，用邮箱兼容内联样式。

    速览可短，分析正文不可再走 ai_points/clip，否则后半段的风险和个人相关性会丢失。
    """
    from bs4 import Comment

    soup = BeautifulSoup(clean_citations(value, news_items), "html.parser")
    for node in soup.find_all(["script", "style", "head", "iframe", "object", "embed", "svg", "math",
                               "img", "video", "audio", "form", "input", "button"]):
        node.decompose()
    for comment in soup.find_all(string=lambda t: isinstance(t, Comment)):
        comment.extract()
    styles = {
        "h3": "margin:20px 0 8px;font-size:19px;font-weight:700;color:#1F2937;line-height:1.6;",
        "p": "margin:10px 0;font-size:18px;color:#374151;line-height:1.75;",
        "ul": "margin:10px 0;padding-left:24px;",
        "ol": "margin:10px 0;padding-left:24px;",
        "li": "margin:8px 0;font-size:18px;color:#374151;line-height:1.75;",
        "strong": "font-weight:700;", "em": "font-style:italic;",
        "span": "color:#8A94A6;font-size:15px;", "br": "",
    }
    for node in list(soup.find_all(True)):
        if node.name in {"h1", "h2", "h4", "h5", "h6"}:
            node.name = "h3"
        if node.name not in styles:
            node.unwrap()
            continue
        node.attrs = {}
        if styles[node.name]:
            node["style"] = styles[node.name]
    return str(soup)
