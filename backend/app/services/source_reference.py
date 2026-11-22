"""Auditable source-type reference, not a truth probability or legacy name score.
Only exact public publisher hosts + documented content paths can match.
Unknown or ambiguous content stays unrated. Checked 2026-11-22.
"""
import ipaddress
import re
from urllib.parse import urlsplit,unquote

POLICY_VERSION='t161-20261122'
# stars, hosts, content path prefixes, source tier, short evidence, public type evidence URL
RULES=(
 (5,('docs.python.org',),('/3/',),'官方技术文档原文','Python 官方文档站及文档路径；只说明出处，不保证结论适用','https://docs.python.org/3/about.html'),
 (4,('arxiv.org','www.arxiv.org'),('/abs/','/pdf/'),'学术原文 / 预印本','arXiv 原文入口；预印本不等于同行评审或结论已证实','https://info.arxiv.org/about/index.html'),
 (3,('www.bbc.com','bbc.com','www.bbc.co.uk'),('/news/','/zhongwen/'),'编辑媒体报道','BBC 媒体站点正文；仍需核对文中原始材料与引用链','https://www.bbc.com/aboutthebbc'),
 (3,('www.jiemian.com','jiemian.com'),('/article/',),'编辑媒体报道','界面新闻机构及报道路径可溯；不推断每篇为独家或一手','https://www.jiemian.com/about/index.html'),
 (3,('www.ithome.com','ithome.com'),('/0/',),'编辑媒体报道','IT之家科技门户及报道路径可溯；原始发布仍需核对','https://www.ithome.com/about.htm'),
 (2,('www.v2ex.com','v2ex.com'),('/t/',),'社区 / 用户发布','V2EX 社区帖子入口；作者身份与原始材料未核验','https://www.v2ex.com/about'),
 (1,('news.ycombinator.com',),('/item',),'二手线索 / 聚合讨论','HN 提交与讨论页，不是所链文章原文；需顺引用链核对','https://news.ycombinator.com/newsguidelines.html'),
)

def safe_url(value):
    if not isinstance(value,str): return ''
    value=value.strip()
    if not value: return ''
    decoded=unquote(value)
    if any(c.isspace() or ord(c)<32 or c in '\\<>"\'' for c in decoded): return ''
    try:
        u=urlsplit(value)
        if u.scheme.lower() not in ('http','https') or not u.hostname or u.username or u.password: return ''
        host=u.hostname.rstrip('.').lower()
        if u.port is not None and not 1 <= u.port <= 65535: return ''
        if host=='localhost' or host.endswith(('.localhost','.local','.internal','.test','.invalid')): return ''
        try:
            if not ipaddress.ip_address(host).is_global: return ''
        except ValueError:
            host.encode('idna')
            if '.' not in host or '%' in host or all(re.fullmatch(r'(?:0x[0-9a-fA-F]+|[0-9]+)',x) for x in host.split('.')): return ''
        return value
    except (ValueError,UnicodeError): return ''


def reference_grade(item):
    url=safe_url(item.get('link'))
    if url:
        u=urlsplit(url);host=u.hostname.rstrip('.').lower()
        for stars,hosts,paths,tier,basis,evidence in RULES:
            if u.scheme.lower()=='https' and host in hosts and any(u.path.startswith(p) if p.endswith('/') else u.path==p for p in paths):
                return dict(stars=stars,symbol='★'*stars+'☆'*(5-stars),label=tier,basis=basis,evidence_url=evidence,policy=POLICY_VERSION)
    return dict(stars=0,symbol='☆☆☆☆☆',label='未评级',basis='没有匹配到已核对的来源类型与正文路径；媒体自称及旧数字权重不作为证据',evidence_url='',policy=POLICY_VERSION)
