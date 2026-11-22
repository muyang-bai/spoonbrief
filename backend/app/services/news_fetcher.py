"""
信息源聚合服务 v2
多源聚合 → 交叉验证 → 去重 → 可信度排序 → 类别均衡 → 输出
"""

from __future__ import annotations
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple

import httpx
import feedparser
from bs4 import BeautifulSoup
from loguru import logger

from app.config import get_settings
from app.models.news_source import NewsSource, SourceType
from app.services.source_credibility import (
    get_credibility
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


