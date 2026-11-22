"""Deterministic evidence preparation and report guide: no extra model request."""
from __future__ import annotations

import hashlib
import html
import json
import re
from datetime import datetime, timedelta, timezone
from bs4 import BeautifulSoup


class AnalysisResult(str):
    def __new__(cls, value, quality=None):
        obj = super().__new__(cls, value)
        obj.quality = quality or {}
        return obj


def pack_materials(items: list, limit: int = 12, budget: int = 14000) -> tuple[str, list]:
    """Bound fields/items, not a serialized JSON byte slice; preserve source identity."""
    selected = []
    for idx, item in enumerate(items[:limit], 1):
        row = {'id': idx, 'title': str(item.get('title') or '')[:220],
               'summary': str(item.get('summary') or '')[:500],
               'source': str(item.get('source') or '来源未提供')[:100],
               'published': str(item.get('published')) if item.get('published') else None, 'link': str(item.get('link') or '')[:500]}
        candidate = json.dumps(selected + [row], ensure_ascii=False)
        if len(candidate) > budget:
            break
        selected.append(row)
    return json.dumps(selected, ensure_ascii=False), selected


def bind_citations(value: str, materials: list) -> tuple[str, list]:
    """Only numbered references bind claims to the original publisher; never invent a publisher."""
    warnings = []
    used = set()
    def ref(match):
        idx = int(match.group(1))
        if not 1 <= idx <= len(materials):
            warnings.append('引用编号超出本期素材范围')
            return '<span> · 引用未匹配</span>'
        used.add(idx)
        src = html.escape(str(materials[idx - 1].get('source') or '来源未提供'))
        if src == '来源未提供':
            warnings.append('引用素材未提供信源名称，不能视为独立核实')
        return f'<span data-sb-src="1" data-sb-material-id="{idx}"> · ' + src + '</span>'
    # Work on text nodes, never attributes. Model HTML will be allowlist-sanitized for email.
    soup = BeautifulSoup(value or '', 'html.parser')
    for node in list(soup.find_all(string=True)):
        if node.parent.name in ('style', 'script', 'head'):
            continue
        text = str(node)
        # A bare named source is not evidence binding, even when its name occurs in the input.
        text = re.sub(r'(?<![\w\u4e00-\u9fff])·\s*([^·<>\n「」。；;，,！？!?\[\]]{1,40})' , ' · 来源未按素材编号核对', text)
        if '来源未按素材编号核对' in text:
            warnings.append('存在未按素材编号核对的来源名')
        escaped = html.escape(text)
        replaced = re.sub(r'\[\s*(\d{1,3})\s*\]', ref, escaped)
        node.replace_with(BeautifulSoup(replaced, 'html.parser'))
    if not used:
        warnings.append('分析未提供可绑定素材编号，观点不应当作已核实事实')
    return str(soup), list(dict.fromkeys(warnings))


def material_key(item: dict) -> str:
    return (str(item.get('link') or '').strip() or str(item.get('title') or '').strip()).lower()


def parsed_date(value):
    if not value:
        return None
    try:
        stamp = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
        if stamp.tzinfo:
            stamp = stamp.astimezone(timezone.utc).replace(tzinfo=None)
        return stamp
    except (ValueError, TypeError):
        return None


def prioritize_materials(items: list, previous: list, now=None) -> list:
    now = now or datetime.utcnow()
    seen = {material_key(i) for i in previous}
    def key(item):
        stamp = parsed_date(item.get('published'))
        valid = stamp and stamp <= now + timedelta(minutes=10)
        age = (now - stamp).total_seconds() if valid else float('inf')
        bucket = 2 if age <= 86400 else 1 if age <= 3 * 86400 else 0
        return (bucket, material_key(item) not in seen, item.get('relevance', 0), str(stamp or ''))
    return sorted(items, key=key, reverse=True)


def freshness(items: list, previous: list, now=None) -> dict:
    now = now or datetime.utcnow()
    seen = {material_key(i) for i in previous}
    published = [parsed_date(i.get('published')) for i in items]
    recent = sum(bool(p and now - timedelta(days=1) <= p <= now + timedelta(minutes=10)) for p in published)
    unknown = sum(p is None or p > now + timedelta(minutes=10) for p in published)
    repeated = sum(material_key(i) in seen for i in items) if previous else 0
    messages = []
    if not recent:
        messages.append('本期素材没有可确认的近24小时新报道，以下为订阅时间窗内回顾，不代表今日新讯。')
    if repeated:
        messages.append(f'本期{repeated}条素材曾在上一份简报素材中出现，观点更新不等同于新增事实。')
    if unknown:
        messages.append(f'{unknown}条素材发布时间缺失或异常，未作为最新消息认定。')
    return {'recent_24h': recent, 'repeated': repeated, 'unknown_date': unknown, 'notice': ''.join(messages)}


def guide_from_analysis(analysis: str, quality: dict, fresh: dict) -> dict:
    """A reading guide, not a second analyst: no new actions, ratings or facts."""
    from app.services.spoonbrief_digest import clip
    soup = BeautifulSoup(analysis or '', 'html.parser')
    headings = [h.get_text(' ', strip=True) for h in soup.find_all(['h2', 'h3'])][:5]
    lead = soup.find(['p', 'li'])
    headline = clip(lead.get_text(' ', strip=True), 140) if lead else ''
    notice = fresh.get('notice', '')
    if quality.get('warnings'):
        notice += '分析状态：' + '；'.join(quality['warnings']) + '。'
    return {'headline': headline, 'brief': [], 'actions': [], 'items_by_idx': {},
            '_guide_from_analysis': True, '_quality': quality, '_freshness': fresh,
            '_notice': notice, '_sections': headings}


def prompt_fingerprint(template) -> str:
    return hashlib.sha256(((template.system_prompt or '') + '\n' + (template.user_prompt_template or '')).encode()).hexdigest()
