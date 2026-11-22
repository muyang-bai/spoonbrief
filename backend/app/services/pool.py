"""
信息池服务：常驻抓取入库（ingest）与简报抽取（query）
"""
from __future__ import annotations
import asyncio
import json
from datetime import datetime, timedelta
from typing import List, Optional, Dict

from loguru import logger
from sqlalchemy.orm import Session

import jieba

from app.models.news_item import NewsItem, NewsEvent, fingerprint_of
from app.services.source_credibility import get_credibility

# 语义归并停用词（单字/无信息量词过滤）
_STOP_WORDS = set(
    "的了是在和与或及等对为以从到被把让向由个些次种年天日时分秒第上下中前后左右内外"
    "今天昨日据悉报道消息显示表示认为记者新闻快讯公司集团官方宣布发布"
    "动态走势情况最新相关资讯信息内容分析解读关注热点"
)


def _keyword_tokens(k: str) -> List[str]:
    """关键词短语 → 匹配词元：整词 + jieba 分词后的 2+ 字实词（去停用词/数字）"""
    toks: List[str] = []
    kl = (k or "").strip().lower()
    if not kl:
        return toks
    toks.append(kl)
    for w in jieba.lcut(kl):
        w = w.strip()
        if len(w) >= 2 and w not in _STOP_WORDS and not w.isdigit() and w not in toks:
            toks.append(w)
    return toks

# t110 · M1：语义归并口径收紧。_STOP_WORDS 是单字集合，对 2 字以上的词不起作用，
# 以前「AI」「美国」「地方」这类泛词也算实体词，两条不同报道共享 2 个泛词就被并成同一事件，
# 「N 源交叉验证」因此虚高。下面这些泛词不参与「实体词交集」判断。
_GENERIC_WORDS = set("""
AI ai 人工智能 智能 大模型 模型 美国 中国 全球 国内 海外 地方 公司 企业 集团 市场 行业 产业 科技 技术 平台 产品
用户 发布 宣布 推出 上线 收购 投资 融资 初创 计划 项目 业务 合作 发展 增长 下降 新款 首款 首个 首届 最新 今年
明年 数据 中心 亿元 万元 美元 政策 消息 报道 回应 透露 表示 计划 推进 加速 升级 全面 正式 重磅 突破 开启
""".split())
_SPECIFIC_MIN_SHARED = 2   # 至少共享 2 个非泛词实体词
_SPECIFIC_MIN_NGRAM = 0.20  # 且字符相似度不能太低


def _same_event(tok: List[str], cand_tokens: List[str], grams: set, cand_grams: set) -> bool:
    """两条标题是否算同一事件（交叉验证口径）。"""
    sim = _ngram_similarity(grams, cand_grams)
    if sim >= _NGRAM_THRESHOLD:
        return True
    specific = {t for t in tok if t not in _GENERIC_WORDS} & {t for t in cand_tokens if t not in _GENERIC_WORDS}
    return len(specific) >= _SPECIFIC_MIN_SHARED and sim >= _SPECIFIC_MIN_NGRAM


# ── 语义相似度 v2：字符 n-gram（本地零成本；将来可替换为 embedding API）──
_NGRAM = 2
_NGRAM_THRESHOLD = 0.40  # Dice 相似度阈值（实测 0.40 为精确甜点：3/3 全对零误判）


def _char_grams(title: str):
    """标题规范化后生成 2-gram 字符集合"""
    import re
    clean = re.sub(r"[^\u4e00-\u9fff\w]", "", title or "").lower()
    if len(clean) < _NGRAM:
        return set()
    return set(clean[i:i + _NGRAM] for i in range(len(clean) - _NGRAM + 1))


def _ngram_similarity(a: set, b: set) -> float:
    """Dice 系数：2*交集 / (两集合大小之和)"""
    if not a or not b:
        return 0.0
    return 2 * len(a & b) / (len(a) + len(b))


def _core_tokens(title: str) -> List[str]:
    """提取标题核心实体词（jieba 分词 + 停用词过滤 + 保序去重，取前 6 个）"""
    words = [
        w for w in jieba.lcut(title or "")
        if len(w) >= 2 and not w.isdigit() and w not in _STOP_WORDS and w.strip()
    ]
    seen, out = set(), []
    for w in words:
        if w not in seen:
            seen.add(w)
            out.append(w)
    return out[:6]


def ingest_sources(db: Session) -> Dict:
    """
    抓取全部激活源并入库。返回统计：{fetched, inserted, sources_used, sources_failed}
    """
    from app.models.news_source import NewsSource
    from app.services.news_fetcher import NewsFetcher

    sources = db.query(NewsSource).filter(NewsSource.is_active == True).all()
    stats = {"fetched": 0, "inserted": 0, "sources_used": [], "sources_failed": []}

    async def _run():
        fetcher = NewsFetcher()
        results = {}
        try:
            for src in sources:
                try:
                    items = await fetcher._fetch_source(src, [], 30)  # 池抓取不设关键词，30 天窗口
                    results[src.id] = (src, items)
                except Exception as e:
                    logger.warning(f"池抓取失败 [{src.name}]: {e}")
                    results[src.id] = (src, [])
        finally:
            await fetcher.close()
        return results

    results = asyncio.new_event_loop().run_until_complete(_run())

    # 预载近 3 天事件用于语义归并（实体词交集 ≥2 判同事件）
    recent_events = db.query(NewsEvent).filter(
        NewsEvent.last_seen_at >= datetime.utcnow() - timedelta(days=3)
    ).all()

    for src_id, (src, items) in results.items():
        if items:
            stats["sources_used"].append(src.name)
            stats["fetched"] += len(items)
        else:
            stats["sources_failed"].append(f"{src.name}(无数据)")

        for it in items:
            fp = fingerprint_of(it.get("title", ""))
            if not fp:
                continue
            exists = db.query(NewsItem).filter(NewsItem.fingerprint == fp).first()
            if not exists:
                db.add(NewsItem(
                    fingerprint=fp,
                    source_id=src.id,
                    source_name=it.get("source") or src.name,
                    title=it.get("title", ""),
                    summary=it.get("summary", ""),
                    link=it.get("link", ""),
                    category=it.get("category") or (src.source_category.value if src.source_category else None),
                    published_at=_parse_published(it.get("published")),
                    credibility=it.get("credibility") or get_credibility(src.name),
                ))
                db.flush()  # autoflush=False：显式 flush，让后续同批次查询看到新行
                stats["inserted"] += 1

            ev = db.query(NewsEvent).filter(NewsEvent.fingerprint == fp).first()
            if ev is None:
                # 精确指纹未命中 → 语义归并两级：
                # 第一级：实体词交集 ≥2；第二级：字符 n-gram 相似度 ≥ 阈值
                tok = _core_tokens(it.get("title", ""))
                grams = _char_grams(it.get("title", ""))
                for cand in recent_events:
                    if cand.fingerprint == fp:
                        continue
                    try:
                        cand_tokens = json.loads(cand.tokens or "[]")
                    except Exception:
                        cand_tokens = []
                    cand_grams = _char_grams(cand.title)
                    if _same_event(tok, cand_tokens, grams, cand_grams):
                        ev = cand
                        logger.debug(f"语义归并: 「{it.get('title', '')[:24]}」 → 事件#{ev.id}「{ev.title[:24]}」")
                        break

            cred = it.get("credibility") or get_credibility(src.name)
            if ev:
                ev.last_seen_at = datetime.utcnow()
                names = json.loads(ev.source_names or "[]")
                if src.name not in names:
                    names.append(src.name)
                    ev.source_names = json.dumps(names, ensure_ascii=False)
                    ev.source_count = len(names)
                if cred > ev.max_credibility:
                    ev.max_credibility = cred
                if not ev.tokens and _core_tokens(it.get("title", "")):
                    ev.tokens = json.dumps(_core_tokens(it.get("title", "")), ensure_ascii=False)
            else:
                ev = NewsEvent(
                    fingerprint=fp,
                    title=it.get("title", ""),
                    category=it.get("category") or (src.source_category.value if src.source_category else None),
                    source_count=1,
                    max_credibility=cred,
                    source_names=json.dumps([src.name], ensure_ascii=False),
                    tokens=json.dumps(_core_tokens(it.get("title", "")), ensure_ascii=False),
                )
                db.add(ev)
                db.flush()
                recent_events.append(ev)
    db.commit()
    stats["cross_source_events"] = db.query(NewsEvent).filter(NewsEvent.source_count >= 2).count()
    logger.info(f"信息池入库: 抓取{stats['fetched']} 新增{stats['inserted']} 池总量{db.query(NewsItem).count()} 多源事件{stats['cross_source_events']}")
    return stats


def extract_interest_words(persona_json: Optional[str]) -> List[str]:
    """从画像提取兴趣词表（用于相关度加权，不进入 prompt）"""
    words: List[str] = []
    if not persona_json:
        return words
    try:
        p = json.loads(persona_json)
    except Exception:
        return words
    interests = p.get("interests")
    if isinstance(interests, list):
        words.extend(str(x).strip().lower() for x in interests if str(x).strip())
    elif isinstance(interests, dict):
        for v in interests.values():
            if isinstance(v, list):
                words.extend(str(x).strip().lower() for x in v if str(x).strip())
            elif isinstance(v, str) and v.strip():
                words.append(v.strip().lower())
    # 身份名称直接入词库（"学生/考研"类画像即使无字段值也加权）
    idents = p.get("identities")
    if isinstance(idents, list):
        words.extend(str(x).strip().lower() for x in idents if str(x).strip())
    for key in ("student", "entrepreneur", "investor", "creator"):
        v = p.get(key)
        if isinstance(v, dict):
            for vv in v.values():
                if isinstance(vv, str) and vv.strip():
                    words.append(vv.strip().lower())
    sd = p.get("self_description")
    if isinstance(sd, str):
        import re
        # 只取 2-4 字的词/词组，避免整句噪声
        words.extend(w.lower() for w in re.findall(r"[a-zA-Z0-9]{2,}|[\u4e00-\u9fff]{2,4}", sd))
    return [w for w in dict.fromkeys(words) if w]


def _parse_published(s: Optional[str]) -> Optional[datetime]:
    if not s:
        return None
    try:
        from app.services.brief_quality import parsed_date
        return parsed_date(s)
    except Exception:
        return None


def query_pool(
    db: Session,
    keywords: Optional[List[str]] = None,
    category_id: Optional[str] = None,
    days: int = 7,
    limit: int = 50,
    persona_words: Optional[List[str]] = None,
) -> List[Dict]:
    """
    从信息池抽取简报素材：类别/时间窗/关键词过滤 → 相关度评分（关键词+画像词库）→ 排序
    相关度 > 0 的条目排在前面（"与你相关"层），其余为广度层
    """
    since = datetime.utcnow() - timedelta(days=days)
    q = db.query(NewsItem, NewsEvent).join(
        NewsEvent, NewsItem.fingerprint == NewsEvent.fingerprint, isouter=True
    )
    # 时间窗：优先按发布时间，无发布时间的按入库时间
    q = q.filter((NewsItem.published_at >= since) | ((NewsItem.published_at == None) & (NewsItem.first_seen_at >= since)))

    q = q.filter((NewsItem.published_at == None) | (NewsItem.published_at <= datetime.utcnow() + timedelta(minutes=10)))

    if category_id:
        matched = q.filter(NewsItem.category == category_id).all()
        if matched:
            rows = matched
        else:
            rows = q.all()  # 类别无数据时回退全部池
    else:
        rows = q.all()

    keywords = [k.strip().lower() for k in (keywords or []) if k.strip()]
    pwords = [w.lower() for w in (persona_words or []) if w]
    kw_tokens_map = {k: _keyword_tokens(k) for k in (keywords or [])}
    items = []
    for item, ev in rows:
        title = item.title or ""
        summary = item.summary or ""
        title_l = title.lower()
        text = title_l + (summary or "").lower()
        # 关键词匹配：整词命中强加分；分词元命中弱加分（长短语/中文逗号输入均可命中）
        # matched 判定收紧：整词命中 或 ≥2 个词元命中（避免单字词元过度匹配）
        relevance = 0
        strong = False
        token_hits = 0
        if keywords:
            for k in keywords:
                if k in title_l:
                    relevance += 5
                    strong = True
                elif k in text:
                    relevance += 2
                    strong = True
                for tok in kw_tokens_map.get(k, []):
                    if tok == k:
                        continue
                    if tok in title_l:
                        relevance += 2
                        token_hits += 1
                    elif tok in text:
                        relevance += 1
                        token_hits += 1
        matched = strong or token_hits >= 2
        if pwords:
            for w in pwords:
                if w in title_l:
                    relevance += 2
                elif w in text:
                    relevance += 1
        items.append({
            "title": title,
            "summary": summary[:500],
            "link": item.link or "",
            "source": item.source_name,
            "category": item.category or "综合",
            "published": item.published_at.isoformat() if item.published_at else None,
            "credibility": item.credibility,
            "_matched": matched,
            "_cross_validated": (ev.source_count >= 2) if ev else False,
            "_source_count": ev.source_count if ev else 1,
            "relevance": relevance,
        })

    # 关键词过滤：有命中则只保留命中条目；无命中回退全部（类别热点），与旧聚合逻辑一致
    if keywords:
        kw_items = [it for it in items if it["_matched"]]
        if kw_items:
            items = kw_items
            logger.info(f"信息池查询: 关键词 {keywords} 命中 {len(items)} 条")

    # Recency buckets before score prevent high-relevance old news monopolizing every issue.
    from app.services.brief_quality import prioritize_materials
    return prioritize_materials(items, [])[:limit]
