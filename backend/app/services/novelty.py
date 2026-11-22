"""事件级新颖性判定（t162）

规则来源（交接标准）：
1. 方向稳定、历史保留：每订阅记录已推送过的事件、来源、已知事实；
2. 文章去重之外还要事件去重：转载/换标题/换措辞/AI 重述都不算新；
3. 同一事件有实质进展才再推：必须出现新来源 + 新日期/新事实，并写清"上次→这次"；
4. 新增要与用户有关：只保留能带来新证据的条目；
5. 没有重要更新时不硬凑：由订阅的 novelty_policy（skip / digest / always）决定。
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timedelta

from app.models.story_memory import StoryMemory
from app.services import entity_link as EL

STOP = set("的了和与及或在是为对将把被从到有也无不这那一个我们你们他们它其以及而且但是因为所以如果就都也很更最非常可以可能已经正在今日今日热点新闻消息报道记者表示称说")

_CN = re.compile(r"[\u4e00-\u9fff]")
_EN = re.compile(r"[a-zA-Z]{2,}")
_NUM = re.compile(r"\d+(?:\.\d+)?")


def _norm(text: str) -> str:
    return re.sub(r"[\s\u3000]+", "", str(text or "")).lower()


def tokens(title: str) -> set:
    t = _norm(title)
    out = set(_EN.findall(t))
    cn = "".join(_CN.findall(t))
    out.update(cn[i:i + 2] for i in range(max(0, len(cn) - 1)))
    out.update(_NUM.findall(t))
    return {x for x in out if x not in STOP}


def jaccard(a: set, b: set) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def similarity(a: set, b: set) -> float:
    """同事件判定：Jaccard 之外加入包含度，避免"同主体+新增细节"被判成不同事件。"""
    jac = jaccard(a, b)
    if not a or not b:
        return 0.0
    containment = len(a & b) / min(len(a), len(b))
    return max(jac, containment * 0.9)


def event_key(title: str) -> str:
    toks = sorted(tokens(title))[:24]
    return hashlib.sha1(("|".join(toks)).encode()).hexdigest()[:40]


def group_events(items: list, threshold: float = 0.5) -> list:
    """把同一事件的多条报道合并成一组，保留全部出处。"""
    groups = []
    for item in items:
        toks = tokens(item.get("title") or "")
        placed = False
        for g in groups:
            sim_score = jaccard(toks, g["tokens"])
            same_hash = EL.hamming(EL.simhash64(item.get("title") or "", toks), g.get("simhash", 0)) <= 6
            ent_a = set(EL.extract_entities(item.get("title") or ""))
            ent_b = set(g.get("entities", []))
            ent_overlap = bool(ent_a & ent_b)
            if sim_score >= threshold or same_hash or (ent_overlap and sim_score >= 0.3):
                g["items"].append(item)
                g["sources"].append({"name": item.get("source"), "link": item.get("link"), "published": item.get("published")})
                g["tokens"] |= toks
                g["entities"] = sorted(set(g.get("entities", [])) | set(EL.extract_entities(item.get("title") or "")))
                placed = True
                break
        if not placed:
            groups.append({"tokens": toks, "items": [item], "key": event_key(item.get("title") or ""),
                           "entities": EL.extract_entities(item.get("title") or ""),
                           "simhash": EL.simhash64(item.get("title") or "", toks),
                           "action": EL.action_class(item.get("title") or ""),
                           "sources": [{"name": item.get("source"), "link": item.get("link"), "published": item.get("published")}]})
    for g in groups:
        g["primary"] = g["items"][0]
        g["source_names"] = sorted({(s.get("name") or "").strip() for s in g["sources"] if s.get("name")})
    return groups


def _parse(value):
    if not value:
        return None
    try:
        stamp = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return stamp.astimezone().replace(tzinfo=None) if stamp.tzinfo else stamp
    except (ValueError, TypeError):
        return None


def load_memory(db, subscription_id: int, days: int = 120) -> dict:
    since = datetime.utcnow() - timedelta(days=days)
    rows = db.query(StoryMemory).filter(
        StoryMemory.subscription_id == subscription_id,
        StoryMemory.last_seen_at >= since,
    ).all()
    return {r.event_key: r for r in rows}


def _row_tokens(row) -> set:
    try:
        return set(json.loads(row.facts_json or "[]"))
    except (ValueError, TypeError):
        return set()


def _row_entities(row) -> list:
    try:
        return json.loads(getattr(row, "entities_json", None) or "[]")
    except (ValueError, TypeError):
        return []


def classify(groups: list, memory: dict, now=None, fuzzy: float = 0.45) -> dict:
    """按事件归类：精确 key 命中，或标题 token 相似度达到阈值即视为同一事件。"""
    now = now or datetime.utcnow()
    if groups and "key" not in (groups[0] or {}):
        groups = group_events(groups)
    fresh, progress, repeat = [], [], []
    index = [(row, _row_tokens(row)) for row in memory.values()]
    for g in groups:
        row = memory.get(g["key"])
        if row is None:
            g_entities = set(g.get("entities") or [])
            g_action = g.get("action") or "其他"
            g_hash = g.get("simhash") or 0
            best, best_sim = None, 0.0
            for candidate, toks in index:
                c_entities = set(_row_entities(candidate))
                c_action = getattr(candidate, "action", None) or "其他"
                # 主体明确不同 → 不是同一事件
                if g_entities and c_entities and not (g_entities & c_entities):
                    continue
                # 动作不同且都不是"其他" → 不合并（腾讯发布 ≠ 腾讯裁员）
                if g_action != "其他" and c_action != "其他" and g_action != c_action:
                    continue
                sim = similarity(g["tokens"], toks)
                try:
                    hash_sim = 1 - EL.hamming(g_hash, int(getattr(candidate, "simhash", 0) or 0)) / 64
                except (TypeError, ValueError):
                    hash_sim = 0.0
                score = max(sim, hash_sim)
                if g_entities & c_entities:
                    score = max(score, 0.46)  # 主体一致时放宽
                if score > best_sim:
                    best, best_sim = candidate, score
            if best is not None and best_sim >= fuzzy:
                row = best
        if row is None:
            fresh.append(g)
            continue
        seen_sources = set(json.loads(row.sources_json or "[]"))
        new_sources = [s for s in g["source_names"] if s not in seen_sources]
        latest = max([d for d in (_parse(s.get("published")) for s in g["sources"]) if d] or [None]) if g["sources"] else None
        newer = bool(latest and row.last_seen_at and latest > row.last_seen_at)
        # 实质进展 = 新来源 + （新日期 或 标题出现新数字/新动作词）
        prev_tokens = set(json.loads(row.facts_json or "[]"))
        delta_tokens = {t for t in (tokens(g["primary"].get("title") or "") - prev_tokens) if _NUM.match(t)}
        moved = bool(new_sources) and (newer or delta_tokens)
        if moved:
            g["previous_title"] = row.title
            g["new_sources"] = new_sources
            g["delta"] = "新增来源：" + "、".join(new_sources[:3]) + ("；出现新数据点" if delta_tokens else "")
            progress.append(g)
        else:
            repeat.append(g)
    return {"fresh": fresh, "progress": progress, "repeat": repeat}


def flatten(groups: list) -> list:
    out = []
    for g in groups:
        item = dict(g["primary"])
        item["sources"] = g["source_names"]
        item["source_count"] = len(g["source_names"])
        if g.get("previous_title"):
            item["_progress_from"] = g["previous_title"]
            item["_progress_delta"] = g.get("delta", "")
        out.append(item)
    return out


def remember(db, subscription_id: int, report_id: int | None, groups: list, now=None) -> int:
    try:
        return _remember(db, subscription_id, report_id, groups, now)
    except Exception:
        db.rollback()
        raise


def _remember(db, subscription_id: int, report_id: int | None, groups: list, now=None) -> int:
    now = now or datetime.utcnow()
    rows = {r.event_key: r for r in db.query(StoryMemory).filter(StoryMemory.subscription_id == subscription_id).all()}
    touched = 0
    for g in groups:
        row = rows.get(g["key"])
        facts = sorted(tokens(g["primary"].get("title") or ""))[:40]
        if row is None:
            row = StoryMemory(subscription_id=subscription_id, event_key=g["key"], title=(g["primary"].get("title") or "")[:300],
                              keywords=",".join(g["source_names"])[:300], first_seen_at=now, last_seen_at=now,
                              last_pushed_at=now, last_report_id=report_id, push_count=1,
                              sources_json=json.dumps(g["source_names"], ensure_ascii=False), facts_json=json.dumps(facts, ensure_ascii=False),
                              entities_json=json.dumps(g.get("entities") or [], ensure_ascii=False),
                              simhash=g.get("simhash") or 0, action=g.get("action") or "其他")
            db.add(row)
        else:
            merged = sorted(set(json.loads(row.sources_json or "[]")) | set(g["source_names"]))
            row.title = (g["primary"].get("title") or row.title or "")[:300]
            row.last_seen_at = now
            row.last_pushed_at = now
            row.last_report_id = report_id
            row.push_count = (row.push_count or 0) + 1
            row.sources_json = json.dumps(merged, ensure_ascii=False)
            row.facts_json = json.dumps(facts, ensure_ascii=False)
            row.entities_json = json.dumps(sorted(set(_row_entities(row)) | set(g.get("entities") or [])), ensure_ascii=False)
            row.simhash = g.get("simhash") or row.simhash
            row.action = g.get("action") or getattr(row, "action", None)
        touched += 1
    db.commit()
    return touched


REASON_LABELS = {
    "direction": "方向不相关",
    "shallow": "太浅，没有增量",
    "stale": "太旧或重复",
    "evidence": "依据不足或有误",
    "length": "太长或太频繁",
}


def feedback_hint(db, user_id: int, subscription_id: int, limit: int = 3) -> str:
    """最近反馈 → 生成策略提示。负反馈只影响接下来几期，不做永久屏蔽。"""
    from app.models.report_feedback import ReportFeedback
    rows = db.query(ReportFeedback).filter(
        ReportFeedback.user_id == user_id,
        (ReportFeedback.subscription_id == subscription_id) | (ReportFeedback.subscription_id.is_(None)),
    ).order_by(ReportFeedback.created_at.desc()).limit(limit).all()
    if not rows:
        return ""
    downs = sum(1 for r in rows if r.value == "down")
    reasons = [getattr(r, "reason", None) for r in rows if r.value == "down"]
    reasons = [REASON_LABELS.get(x, x) for x in reasons if x]
    parts = [f"最近 {len(rows)} 次反馈中 {downs} 次标记为没用。"]
    if reasons:
        parts.append("读者给出的原因：" + "、".join(reasons[:3]) + "。")
    parts.append("请据此调整：减少已报道内容、提高选材门槛、补充背景与影响、控制篇幅。")
    return "".join(parts)
