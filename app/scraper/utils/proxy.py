"""Proxy rotation for enterprise scraping."""

from __future__ import annotations

import itertools
import random
import threading
from urllib.parse import urlparse

from app.core.config import get_settings

_lock = threading.Lock()
_cycle: itertools.cycle | None = None


def _parse_proxy_list(raw: str) -> list[str]:
    proxies: list[str] = []
    for part in raw.replace("\n", ",").split(","):
        p = part.strip()
        if not p:
            continue
        if "://" not in p:
            p = f"http://{p}"
        proxies.append(p)
    return proxies


def get_proxy_pool() -> list[str]:
    settings = get_settings()
    raw = getattr(settings, "SCRAPER_PROXY_URLS", "") or ""
    return _parse_proxy_list(raw)


def get_next_proxy() -> str | None:
    global _cycle
    pool = get_proxy_pool()
    if not pool:
        return None
    with _lock:
        if _cycle is None:
            random.shuffle(pool)
            _cycle = itertools.cycle(pool)
        return next(_cycle)


def proxy_dict_for_requests(proxy_url: str | None) -> dict[str, str] | None:
    if not proxy_url:
        return None
    return {"http": proxy_url, "https": proxy_url}


def reset_proxy_cycle() -> None:
    global _cycle
    with _lock:
        _cycle = None


def is_residential_proxy(proxy_url: str) -> bool:
    host = urlparse(proxy_url).hostname or ""
    markers = ("residential", "brightdata", "oxylabs", "smartproxy", "geonode")
    return any(m in host.lower() for m in markers)
