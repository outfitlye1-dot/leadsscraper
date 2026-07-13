"""robots.txt parsing and URL allow checks."""

from __future__ import annotations

import logging
import re
import threading
import time
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import requests

from app.scraper.utils.user_agents import get_random_user_agent

logger = logging.getLogger(__name__)

_cache: dict[str, tuple[float, RobotFileParser | None]] = {}
_lock = threading.Lock()
_CACHE_TTL = 3600


def _robots_url(url: str) -> str:
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}/robots.txt"


def _fetch_robots(robots_url: str, timeout: float = 6.0) -> RobotFileParser | None:
    try:
        resp = requests.get(
            robots_url,
            timeout=timeout,
            headers={"User-Agent": get_random_user_agent()},
        )
        if resp.status_code >= 400:
            return None
        parser = RobotFileParser()
        parser.parse(resp.text.splitlines())
        return parser
    except Exception as exc:
        logger.debug("robots.txt fetch failed %s: %s", robots_url, exc)
        return None


def get_robots_parser(url: str) -> RobotFileParser | None:
    robots_url = _robots_url(url)
    now = time.time()
    with _lock:
        cached = _cache.get(robots_url)
        if cached and now - cached[0] < _CACHE_TTL:
            return cached[1]

    parser = _fetch_robots(robots_url)
    with _lock:
        _cache[robots_url] = (now, parser)
    return parser


def is_allowed(url: str, user_agent: str = "*") -> bool:
    parser = get_robots_parser(url)
    if parser is None:
        return True
    try:
        return parser.can_fetch(user_agent, url)
    except Exception:
        return True


def crawl_delay(url: str, user_agent: str = "*") -> float | None:
    parser = get_robots_parser(url)
    if parser is None:
        return None
    try:
        delay = parser.crawl_delay(user_agent)
        return float(delay) if delay else None
    except Exception:
        return None


def extract_sitemaps(url: str) -> list[str]:
    robots_url = _robots_url(url)
    try:
        resp = requests.get(robots_url, timeout=6.0, headers={"User-Agent": get_random_user_agent()})
        if resp.status_code >= 400:
            return []
        sitemaps: list[str] = []
        for line in resp.text.splitlines():
            m = re.match(r"^\s*Sitemap:\s*(\S+)", line, re.I)
            if m:
                sitemaps.append(m.group(1).strip())
        return sitemaps
    except Exception:
        return []
