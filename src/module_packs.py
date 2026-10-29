"""NOMIKO local declarative domain-blocking packs (never executable extensions)."""
from __future__ import annotations

import re
from pathlib import Path

MAX_LIST_BYTES = 2 * 1024 * 1024
MAX_ENTRIES = 22000
DOMAIN = re.compile(r'^(?=.{4,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z][a-z0-9-]{1,62}$')


def parse_hosts_file(data: str) -> frozenset[str]:
    if len(data.encode('utf-8')) > MAX_LIST_BYTES:
        raise ValueError('List exceeds 2 MB')
    domains = set()
    for raw_line in data.splitlines():
        line = raw_line.split('#', 1)[0].strip().lower()
        if not line or line.startswith(('!', '[', '||', '@@')): continue
        parts = line.split()
        if parts and parts[0] in ('127.0.0.1', '0.0.0.0', '::1') and len(parts) > 1:
            parts = parts[1:]
        if not parts: continue
        domain = parts[0].rstrip('.')
        if DOMAIN.fullmatch(domain):
            domains.add(domain)
        if len(domains) > MAX_ENTRIES:
            raise ValueError('List exceeds 22,000 domains')
    return frozenset(domains)


def load_hosts(path: Path) -> frozenset[str]:
    if not path.exists(): return frozenset()
    if path.stat().st_size > MAX_LIST_BYTES:
        raise ValueError('List exceeds 2 MB')
    return parse_hosts_file(path.read_text(encoding='utf-8-sig', errors='replace'))


def match_host(host: str, domains: frozenset[str]) -> bool:
    """O(depth) suffix lookup, not O(number of blocked hosts) per request."""
    host = str(host).strip('.').lower()
    parts = host.split('.')
    return any('.'.join(parts[i:]) in domains for i in range(len(parts)-1))
