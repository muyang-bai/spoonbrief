"""
信息源可信度评分与交叉验证
"""

from __future__ import annotations

# 来源域名/名称 → 可信度权重（1-10）
# 分级标准：官方喉舌(10) > 权威媒体(9) > 一线媒体(8) > 专业垂直媒体(7) >
#           科技媒体(6) > 商业/聚合(5) > 社区/自定义(4)
SOURCE_CREDIBILITY = {
    # ── 官方媒体（10）──
    "央视新闻": 10, "央视": 10, "CCTV": 10, "cctv": 10,
    "人民日报": 10, "新华社": 10, "Xinhua": 10,
    # ── 权威媒体（9）──
    "中新网": 9, "财新网": 9, "caixin": 9,
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


def _event_fingerprint(title: str, length: int = 15) -> str:
    """事件指纹：取标题前N字，去除标点和空格"""
    import re
    clean = re.sub(r'[^\u4e00-\u9fff\w]', '', title)
    return clean[:length].lower()
