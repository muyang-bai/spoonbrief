"""实体链接与 SimHash（t180）

参考开源实践：
- HarvestText 的"别名词典 → 实体链接"思路（中文场景、弱监督即可）
- SimHash 近重复检测（news-aggregator 用 SimHash 把同一新闻聚类成 story）
- MinHash/LSH 的候选思想在这里简化为：SimHash 汉明距离先筛，再算 token 相似度

目标：同一事件换标题、转载、改写也能合并；不同公司/不同动作不会被误合并。
"""
from __future__ import annotations

import hashlib
import re
from typing import Iterable

# 领域别名词典（可持续扩充；生产环境可改为读 entity_aliases 表）
ENTITY_SEED: list[tuple[str, list[str], str]] = [
    ("腾讯", ["腾讯", "tencent", "腾讯控股", "腾讯集团", "微信", "wechat"], "company"),
    ("阿里巴巴", ["阿里", "阿里巴巴", "alibaba", "淘宝", "天猫", "阿里云"], "company"),
    ("字节跳动", ["字节", "字节跳动", "bytedance", "抖音", "tiktok", "豆包"], "company"),
    ("DeepSeek", ["deepseek", "深度求索", "深度搜索"], "company"),
    ("OpenAI", ["openai", "chatgpt", "gpt-4", "gpt-5", "sora"], "company"),
    ("Anthropic", ["anthropic", "claude"], "company"),
    ("英伟达", ["英伟达", "nvidia", "黄仁勋"], "company"),
    ("华为", ["华为", "huawei", "鸿蒙", "harmonyos"], "company"),
    ("苹果", ["苹果", "apple", "iphone", "vision pro"], "company"),
    ("小米", ["小米", "xiaomi", "雷军"], "company"),
    ("百度", ["百度", "baidu", "文心一言"], "company"),
    ("蚂蚁集团", ["蚂蚁", "蚂蚁集团", "支付宝", "ant group"], "company"),
    ("美团", ["美团", "meituan"], "company"),
    ("京东", ["京东", "jd.com"], "company"),
    ("拼多多", ["拼多多", "pinduoduo", "temu"], "company"),
    ("特斯拉", ["特斯拉", "tesla", "马斯克", "musk"], "company"),
    ("宁德时代", ["宁德时代", "catl"], "company"),
    ("台积电", ["台积电", "tsmc"], "company"),
    ("中芯国际", ["中芯国际", "smic"], "company"),
    ("小鹏", ["小鹏", "xpeng", "小鹏汇天"], "company"),
    ("低空经济", ["低空经济", "eVTOL", "飞行汽车"], "policy"),
    ("大模型", ["大模型", "基础模型", "llm", "多模态模型"], "tech"),
    ("算力", ["算力", "智算", "数据中心", "gpu集群"], "tech"),
    ("芯片", ["芯片", "半导体", "晶圆", "先进制程"], "tech"),
    ("机器人", ["机器人", "人形机器人", "具身智能"], "tech"),
    ("央行", ["央行", "中国人民银行", "人民银行", "降准", "降息"], "org"),
    ("证监会", ["证监会", "证券监督管理委员会"], "org"),
    ("教育部", ["教育部"], "org"),
    ("工信部", ["工信部", "工业和信息化部"], "org"),
    ("发改委", ["发改委", "国家发展改革委"], "org"),
    ("财政部", ["财政部"], "org"),
]

ACTION_SEED: list[tuple[str, list[str]]] = [
    ("发布", ["发布", "推出", "上线", "开源", "公布", "亮相", "首发"]),
    ("收购", ["收购", "并购", "入股", "买下", "合并"]),
    ("融资", ["融资", "获投", "完成a轮", "完成b轮", "完成c轮", "估值", "上市"]),
    ("涨价", ["涨价", "提价", "上调", "价格上调"]),
    ("降价", ["降价", "下调", "价格战", "补贴"]),
    ("裁员", ["裁员", "优化人员", "缩减团队", "降本"]),
    ("政策", ["新政", "政策", "条例", "办法", "试点", "监管", "征求意见"]),
    ("数据", ["同比", "环比", "增长", "下降", "创新高", "突破", "翻倍"]),
    ("处罚", ["处罚", "罚款", "起诉", "诉讼", "判赔", "约谈"]),
    ("合作", ["合作", "签约", "战略协议", "共建"]),
]

_PUNCT = re.compile(r"[\s\u3000,，。.!！?？:：;；\"'“”‘’()（）\[\]【】<>《》、/\\|\-—_~`@#$%^&*+=]+")


def normalize(text: str) -> str:
    t = (text or "").lower()
    # 全角转半角
    t = t.translate({0xFF01 + i: 0x21 + i for i in range(94)})
    return _PUNCT.sub("", t)


def build_alias_map(rows: Iterable[tuple[str, str]] | None = None) -> list[tuple[str, str]]:
    """返回 [(alias_norm, canonical)]，长别名优先匹配。"""
    pairs: list[tuple[str, str]] = []
    for canonical, aliases, _type in ENTITY_SEED:
        for alias in aliases:
            pairs.append((normalize(alias), canonical))
    if rows:
        for alias, canonical in rows:
            pairs.append((normalize(alias), canonical))
    pairs = [(a, c) for a, c in pairs if a]
    pairs.sort(key=lambda x: len(x[0]), reverse=True)
    return pairs


_ALIASES = build_alias_map()


def extract_entities(text: str, aliases: list[tuple[str, str]] | None = None) -> list[str]:
    t = normalize(text)
    if not t:
        return []
    found: list[str] = []
    used = [False] * len(t)
    for alias, canonical in (aliases or _ALIASES):
        start = 0
        while True:
            idx = t.find(alias, start)
            if idx < 0:
                break
            if not any(used[idx:idx + len(alias)]):
                for i in range(idx, idx + len(alias)):
                    used[i] = True
                if canonical not in found:
                    found.append(canonical)
            start = idx + len(alias)
    return found


def action_class(text: str) -> str:
    t = normalize(text)
    for name, words in ACTION_SEED:
        if any(normalize(w) in t for w in words):
            return name
    return "其他"


def _hash64(token: str) -> int:
    return int.from_bytes(hashlib.md5(token.encode("utf-8")).digest()[:8], "big")


def simhash64(text: str, tokens: Iterable[str] | None = None) -> int:
    """64 位 SimHash：标题换序/轻微改写后汉明距离仍然很小。"""
    from app.services.novelty import tokens as _tokens
    toks = list(tokens or _tokens(text))
    if not toks:
        return 0
    weights = [0] * 64
    for tok in toks:
        h = _hash64(tok)
        for bit in range(64):
            weights[bit] += 1 if (h >> bit) & 1 else -1
    out = 0
    for bit in range(64):
        if weights[bit] > 0:
            out |= 1 << bit
    return out


def hamming(a: int, b: int) -> int:
    return bin((a or 0) ^ (b or 0)).count("1")
