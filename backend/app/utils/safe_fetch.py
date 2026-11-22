"""Public RSS URL guard: block local networks and re-check every redirect, bound response size."""
from __future__ import annotations
import ipaddress
import socket
from urllib.parse import urlsplit, urljoin
import httpx


def validate_public_url(url: str) -> str:
    parts = urlsplit(url)
    if parts.scheme not in ('http', 'https') or not parts.hostname or parts.username or parts.password:
        raise ValueError('RSS地址必须是无用户名密码的公开http(s)地址')
    if parts.port not in (None, 80, 443):
        raise ValueError('RSS仅支持80/443端口')
    addresses = socket.getaddrinfo(parts.hostname, parts.port or (443 if parts.scheme == 'https' else 80), type=socket.SOCK_STREAM)
    if not addresses or any(not ipaddress.ip_address(row[4][0]).is_global for row in addresses):
        raise ValueError('RSS不允许访问本机、内网或保留地址')
    return url


def fetch_public_rss(url: str) -> bytes:
    with httpx.Client(timeout=15, trust_env=False, headers={'User-Agent': 'SpoonBrief-RSS/1.0'}) as client:
        for _ in range(5):
            validate_public_url(url)
            with client.stream('GET', url, follow_redirects=False) as resp:
                if resp.is_redirect:
                    url = urljoin(url, resp.headers.get('location', ''))
                    continue
                resp.raise_for_status()
                chunks = []
                size = 0
                for chunk in resp.iter_bytes():
                    size += len(chunk)
                    if size > 2 * 1024 * 1024:
                        raise ValueError('RSS响应超过2MB限制')
                    chunks.append(chunk)
                return b''.join(chunks)
    raise ValueError('RSS重定向次数过多')
