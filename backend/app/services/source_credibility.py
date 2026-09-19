"""
信息源可信度评分与交叉验证
"""

from __future__ import annotations
from typing import List, Dict, Set, Tuple
from loguru import logger

# 来源域名/名称 → 可信度权重（1-10）
# 分级标准：官方喉舌(10) > 权威媒体(9) > 一线媒体(8) > 专业垂直媒体(7) >
#           科技媒体(6) > 商业/聚合(5) > 社区/自定义(4)
SOURCE_CREDIBILITY = {
    # ── 官方媒体（10）──
    "央视新闻": 10, "央视": 10, "CCTV": 10, "cctv": 10,
    "人民日报": 10, "新华社": 10, "Xinhua": 10,
    # ── 权威媒体（9）──
    "中新网": 9, "财新网": 9, "caixin": 9, "新华社": 10,
    "BBC": 9, "bbc": 9, "FT中文": 9, "ftchinese": 9,
    "纽约时报中文": 8, "nytimes": 8, "联合早报": 8, "zaobao": 8,
    # ── 一线媒体（8）──
    "澎湃新闻": 8, "澎湃": 8, "thepaper": 8,
    # ── 专业垂直媒体（7）──
    "36氪": 7, "36kr": 7, "财联社": 7, "cls": 7, "界面新闻": 7, "jiemian": 7,
    "InfoQ": 7, "infoq": 7, "晚点": 7, "latepost": 7,
    # ── 科技媒体（6）──
    "IT之家": 6, "ithome": 6, "开源中国": 6, "oschina": 6, "量子位": 6, "qbitai": 6,
    "极客公园": 6, "geekpark": 6, "爱范儿": 6, "ifanr": 6, "少数派": 6, "sspai": 6,
    "新浪科技": 6, "sina": 6, "虎嗅": 6, "huxiu": 6, "机器之心": 6, "jiqizhixin": 6,
    # ── 商业/聚合（5）──
    "雷锋网": 5, "leiphone": 5, "快科技": 5, "mydrivers": 5,
    "DailyHot": 5, "NewsAPI": 6, "Bing": 6,
    # ── 社区/用户自定义（4）──
    "雪球热帖": 4, "xueqiu": 4, "V2EX": 4, "v2ex": 4,
    "自定义": 4, "default": 4,
}


def get_credibility(source_name: str) -> int:
    """根据来源名称返回可信度评分（名称映射，未命中回退 4 并标注）"""
    for key, score in SOURCE_CREDIBILITY.items():
        if key.lower() in source_name.lower():
            return score
    return SOURCE_CREDIBILITY["default"]


def cross_validate(news_items: List[Dict], min_sources: int = 2) -> List[Dict]:
    """
    交叉验证：同一事件至少被 min_sources 个独立来源报道才采信
    通过标题相似度判断是否为同一事件
    """
    if not news_items:
        return []

    validated = []
    # 用标题前15字作为事件指纹
    event_groups: Dict[str, List[Dict]] = {}
    for item in news_items:
        fingerprint = _event_fingerprint(item.get("title", ""))
        if fingerprint not in event_groups:
            event_groups[fingerprint] = []
        event_groups[fingerprint].append(item)

    for fingerprint, items in event_groups.items():
        source_names = set(item.get("source", "") for item in items)
        # 至少 N 个不同来源
        if len(source_names) >= min_sources:
            # 选可信度最高的那条作为代表作
            best = max(items, key=lambda x: get_credibility(x.get("source", "")))
            best["_cross_validated"] = True
            best["_source_count"] = len(source_names)
            best["_all_sources"] = list(source_names)
            validated.append(best)
        else:
            # 只有1个来源的，降低权重但保留（附标记）
            for item in items:
                item["_cross_validated"] = False
                item["_source_count"] = 1
                validated.append(item)

    logger.info(f"交叉验证: {len(news_items)}条 → {len(validated)}条通过 (≥{min_sources}源: {sum(1 for v in validated if v.get('_cross_validated'))})")
    return validated


def balance_by_category(news_items: List[Dict], max_per_category: int = 15) -> List[Dict]:
    """按类别均衡采样，确保信息多样性"""
    from collections import defaultdict
    buckets: Dict[str, List[Dict]] = defaultdict(list)
    for item in news_items:
        cat = item.get("category", "综合")
        buckets[cat].append(item)

    balanced = []
    for cat, items in buckets.items():
        # 按可信度排序取前 N
        items.sort(key=lambda x: x.get("_cross_validated", False), reverse=True)
        balanced.extend(items[:max_per_category])

    logger.info(f"类别均衡: {len(news_items)}条 → {len(balanced)}条 (类别数: {len(buckets)})")
    return balanced


def sort_by_credibility(news_items: List[Dict]) -> List[Dict]:
    """按可信度 + 交叉验证排序"""
    return sorted(
        news_items,
        key=lambda x: (
            x.get("_cross_validated", False),
            get_credibility(x.get("source", "")),
            x.get("_source_count", 0),
        ),
        reverse=True,
    )


def deduplicate(news_items: List[Dict]) -> List[Dict]:
    """去重：基于标题相似度"""
    seen = set()
    unique = []
    for item in news_items:
        fp = _event_fingerprint(item.get("title", ""))
        if fp not in seen:
            seen.add(fp)
            unique.append(item)
    return unique


def _event_fingerprint(title: str, length: int = 15) -> str:
    """事件指纹：取标题前N字，去除标点和空格"""
    import re
    clean = re.sub(r'[^\u4e00-\u9fff\w]', '', title)
    return clean[:length].lower()
