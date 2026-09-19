"""
信息源聚合服务 v2
多源聚合 → 交叉验证 → 去重 → 可信度排序 → 类别均衡 → 输出
"""

from __future__ import annotations
import asyncio
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple

import httpx
import feedparser
from bs4 import BeautifulSoup
from loguru import logger

from app.config import get_settings
from app.models.news_source import NewsSource, SourceType, SourceCategory
from app.services.source_credibility import (
    cross_validate, balance_by_category, sort_by_credibility, deduplicate, get_credibility
)

settings = get_settings()

# 简单内存缓存：key → (items, expire_time)
_cache: Dict[str, Tuple[List[Dict], float]] = {}
_CACHE_TTL = 1800  # 30 分钟


def _strip_html(text: str) -> str:
    return BeautifulSoup(text or "", "html.parser").get_text(strip=True)


def _within_days(published: Optional[datetime], days: int) -> bool:
    if not published:
        return True
    return published >= datetime.utcnow() - timedelta(days=days)


def _update_api_remaining(source: NewsSource, remaining: int):
    """更新信息源的 API 剩余次数"""
    from app.database import SessionLocal
    db = SessionLocal()
    try:
        s = db.query(NewsSource).get(source.id)
        if s:
            s.api_remaining = remaining
            s.api_remaining_updated = datetime.utcnow()
            db.commit()
    except Exception:
        pass
    finally:
        db.close()


def _touch_last_fetch(source: NewsSource):
    """记录信息源最近抓取时间（可观测性）"""
    from app.database import SessionLocal
    db = SessionLocal()
    try:
        s = db.query(NewsSource).get(source.id)
        if s:
            s.last_fetch_at = datetime.utcnow()
            db.commit()
    except Exception:
        pass
    finally:
        db.close()


def _cache_key(source_id: int, keywords: List[str], days: int) -> str:
    return f"src_{source_id}_kw_{'_'.join(sorted(keywords))}_d{days}"


def _from_cache(key: str) -> Optional[List[Dict]]:
    if key in _cache:
        items, expire = _cache[key]
        if time.time() < expire:
            return items
        del _cache[key]
    return None


def _to_cache(key: str, items: List[Dict]):
    _cache[key] = (items, time.time() + _CACHE_TTL)


class NewsFetcher:
    def __init__(self):
        self.client: Optional[httpx.AsyncClient] = None

    async def _ensure_client(self):
        if self.client is None:
            self.client = httpx.AsyncClient(
                timeout=30,
                follow_redirects=True,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                                  "(KHTML, like Gecko) Chrome/124.0 Safari/537.36 SpoonBrief/2.0",
                    "Accept": "application/rss+xml, application/xml, text/xml, */*",
                },
            )

    async def close(self):
        if self.client:
            await self.client.aclose()
            self.client = None

    # ═══════ RSS ═══════
    async def fetch_rss(self, source: NewsSource, keywords: List[str], days: int) -> List[Dict]:
        await self._ensure_client()
        try:
            resp = await self.client.get(source.url, follow_redirects=True)
            feed = feedparser.parse(resp.text)
            results = []
            for entry in feed.entries:
                published = None
                if hasattr(entry, "published_parsed") and entry.published_parsed:
                    published = datetime(*entry.published_parsed[:6])
                if not _within_days(published, days):
                    continue
                title = entry.get("title", "")
                summary = _strip_html(entry.get("summary", ""))[:500]
                link = entry.get("link", "")
                text = (title + summary).lower()
                results.append(dict(
                    title=title, summary=summary, link=link,
                    source=source.name, category=source.source_category.value,
                    published=published.isoformat() if published else None,
                    credibility=get_credibility(source.name),
                    _matched=any(kw.lower() in text for kw in keywords) if keywords else True,
                ))
            logger.info(f"RSS [{source.name}] 获取 {len(results)} 条")
            return results
        except Exception as e:
            logger.warning(f"RSS [{source.name}] 获取失败（可能反爬或网络问题）: {e}")
            return []

    # ═══════ DailyHotApi ═══════
    async def fetch_dailyhot(self, source: NewsSource, keywords: List[str], days: int) -> List[Dict]:
        await self._ensure_client()
        results = []
        search_kws = keywords if keywords else ["热点"]
        for kw in search_kws:
            try:
                url = f"{settings.dailyhot_base_url}/search/{kw}"
                resp = await self.client.get(url, params={"count": 20})
                data = resp.json()
                for item in data.get("data", []):
                    published = None
                    if item.get("pubDate"):
                        try:
                            published = datetime.fromtimestamp(item["pubDate"] / 1000)
                        except Exception:
                            pass
                    if not _within_days(published, days):
                        continue
                    title = item.get("title", "")
                    results.append(dict(
                        title=title,
                        summary=_strip_html(item.get("description", ""))[:500],
                        link=item.get("url", ""),
                        source=f"DailyHot-{item.get('source', source.name)}",
                        category=source.source_category.value,
                        published=published.isoformat() if published else None,
                        credibility=get_credibility("DailyHot"),
                        _matched=True,
                    ))
            except Exception as e:
                logger.warning(f"DailyHotApi [{kw}] 失败: {e}")
        return results

    # ═══════ NewsAPI ═══════
    async def fetch_newsapi(self, source: NewsSource, keywords: List[str], days: int) -> List[Dict]:
        if not settings.newsapi_key:
            return []
        await self._ensure_client()
        results = []
        for kw in (keywords or ["热点"]):
            try:
                from_param = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%d")
                resp = await self.client.get(
                    "https://newsapi.org/v2/everything",
                    params=dict(q=kw, from_=from_param, sortBy="publishedAt",
                                apiKey=settings.newsapi_key, language="zh", pageSize=20),
                )
                data = resp.json()
                if data.get("status") == "error":
                    logger.warning(f"NewsAPI: {data.get('message', 'unknown error')}")
                    continue
                total_results = data.get("totalResults", 0)
                for article in data.get("articles", []):
                    published = None
                    if article.get("publishedAt"):
                        try:
                            published = datetime.fromisoformat(
                                article["publishedAt"].replace("Z", "+00:00")
                            ).replace(tzinfo=None)
                        except Exception:
                            pass
                    results.append(dict(
                        title=article.get("title", ""),
                        summary=_strip_html(article.get("description", ""))[:500],
                        link=article.get("url", ""),
                        source=f"NewsAPI-{article.get('source', {}).get('name', '未知')}",
                        category=source.source_category.value,
                        published=published.isoformat() if published else None,
                        credibility=get_credibility("NewsAPI"),
                        _matched=True,
                    ))
                logger.info(f"NewsAPI [{kw}] 获取 {len(results)}条 (总{total_results}条)")
            except Exception as e:
                logger.warning(f"NewsAPI [{kw}] 请求失败: {e}")
        return results

    # ═══════ Bing News ═══════
    async def fetch_bing_news(self, source: NewsSource, keywords: List[str], days: int) -> List[Dict]:
        if not settings.bing_news_key:
            return []
        await self._ensure_client()
        results = []
        for kw in (keywords or ["热点"]):
            try:
                headers = {"Ocp-Apim-Subscription-Key": settings.bing_news_key}
                resp = await self.client.get(
                    "https://api.bing.microsoft.com/v7.0/news/search",
                    params=dict(q=kw, count=20, mkt="zh-CN"), headers=headers,
                )
                data = resp.json()
                for article in data.get("value", []):
                    published = None
                    if article.get("datePublished"):
                        try:
                            published = datetime.fromisoformat(
                                article["datePublished"].replace("Z", "+00:00")
                            ).replace(tzinfo=None)
                        except Exception:
                            pass
                    results.append(dict(
                        title=article.get("name", ""),
                        summary=_strip_html(article.get("description", ""))[:500],
                        link=article.get("url", ""),
                        source=f"Bing-{article.get('provider', [{}])[0].get('name', '未知')}",
                        category=source.source_category.value,
                        published=published.isoformat() if published else None,
                        credibility=get_credibility("Bing"),
                        _matched=True,
                    ))
                logger.info(f"BingNews [{kw}] 获取 {len(results)} 条")
            except Exception as e:
                logger.warning(f"BingNews [{kw}] 失败: {e}")
        return results

    # ═══════ 单源分发 ═══════
    async def _fetch_source(self, source: NewsSource, keywords: List[str], days: int) -> List[Dict]:
        cache_key = _cache_key(source.id, keywords, days)
        cached = _from_cache(cache_key)
        if cached is not None:
            logger.debug(f"缓存命中: {source.name}")
            return cached

        if source.source_type == SourceType.RSS:
            items = await self.fetch_rss(source, keywords, days)
        elif source.source_type == SourceType.DAILYHOT:
            items = await self.fetch_dailyhot(source, keywords, days)
        elif source.source_type == SourceType.NEWSAPI:
            items = await self.fetch_newsapi(source, keywords, days)
        elif source.source_type == SourceType.BING_NEWS:
            items = await self.fetch_bing_news(source, keywords, days)
        else:
            items = []

        _to_cache(cache_key, items)
        _touch_last_fetch(source)
        return items

    # ═══════ 全局聚合入口 ═══════
    async def aggregate(
        self,
        sources: List[NewsSource],
        keywords: List[str],
        days: int,
        category_id: Optional[str] = None,
    ) -> dict:
        """
        主入口：聚合 → 验证 → 去重 → 排序 → 均衡，返回 dict 包含 items 和 stats
        """
        stats = {"total_fetched": 0, "after_validation": 0, "after_balance": 0,
                 "sources_used": [], "sources_failed": [], "category": category_id}

        # 过滤匹配类别的源；该类别无源时回退到全部可用源（保证任何订阅都有数据）
        active_sources = [s for s in sources if s.is_active]
        if category_id:
            matching = [s for s in active_sources if s.source_category.value == category_id]
            comprehensive = [s for s in active_sources if s.source_category.value == "综合"]
            if matching:
                active_sources = list({s.id: s for s in matching + comprehensive}.values())
            else:
                logger.warning(f"类别 {category_id} 无专属信息源，回退到全部 {len(active_sources)} 个源")
                stats["category_fallback"] = True

        tasks = []
        for src in active_sources:
            tasks.append(self._fetch_source(src, keywords, days))

        results_lists = await asyncio.gather(*tasks, return_exceptions=True)
        all_news = []
        for i, r in enumerate(results_lists):
            src_name = active_sources[i].name if i < len(active_sources) else "?"
            if isinstance(r, list):
                if r:
                    all_news.extend(r)
                    stats["sources_used"].append(src_name)
                else:
                    stats["sources_failed"].append(f"{src_name}(无数据)")
            else:
                stats["sources_failed"].append(f"{src_name}(异常)")

        stats["total_fetched"] = len(all_news)

        # 去重
        all_news = deduplicate(all_news)

        # 交叉验证（≥2 源采信）
        all_news = cross_validate(all_news, min_sources=2)
        stats["after_validation"] = len(all_news)

        # 可信度排序
        all_news = sort_by_credibility(all_news)

        # 类别均衡采样
        all_news = balance_by_category(all_news, max_per_category=15)
        stats["after_balance"] = len(all_news)

        # 限制总数 50 条
        final = all_news[:50]

        # 如果没有精确匹配，回退到类别热点（不带关键词宽泛拉取）
        if keywords and not any(item.get("_matched") for item in final):
            logger.info(f"关键词 '{keywords}' 无精确匹配，回退到类别 {category_id} 综合热点")
            fallback = []
            for src in active_sources:
                broad = await self._fetch_source(src, [], days)
                fallback.extend(broad)
            fallback = deduplicate(fallback)
            fallback = sort_by_credibility(fallback)
            final = fallback[:50]
            stats["fallback"] = True
            stats["after_balance"] = len(final)

        # 无数据时诚实返回空（不再伪造演示数据），由上层给出明确的失败原因
        if not final:
            logger.warning(f"所有信息源均无数据，返回空结果（sources_failed={stats['sources_failed']}）")

        logger.info(f"聚合完成: 获取{stats['total_fetched']}条 → 验证后{stats['after_validation']}条 → 均衡后{stats['after_balance']}条")
        return {"items": final, "stats": stats}

def _dev_fallback_data(keywords: list, category_id: str = None) -> list:
    """[已废弃] 本地兜底测试数据：不再使用，信息源无数据时诚实返回空"""
    return []




_news_fetcher: Optional[NewsFetcher] = None


async def get_news_fetcher() -> NewsFetcher:
    global _news_fetcher
    if _news_fetcher is None:
        _news_fetcher = NewsFetcher()
    return _news_fetcher
