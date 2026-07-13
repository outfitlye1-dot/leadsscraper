"""BFS crawl frontier with depth control and URL normalization."""

from __future__ import annotations

import re
from collections import deque
from dataclasses import dataclass, field
from urllib.parse import urljoin, urlparse, urlunparse

_TRACKING_PARAMS = frozenset(
    {"utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content", "fbclid", "gclid"}
)


def normalize_url(url: str, base: str | None = None) -> str:
    if base:
        url = urljoin(base, url)
    parsed = urlparse(url.strip())
    if not parsed.scheme:
        parsed = urlparse(f"https://{url.strip()}")
    host = (parsed.netloc or "").lower()
    path = parsed.path or "/"
    if path != "/" and path.endswith("/"):
        path = path.rstrip("/")
    # drop fragments; keep useful query params
    query_parts = []
    if parsed.query:
        for part in parsed.query.split("&"):
            if not part:
                continue
            key = part.split("=", 1)[0].lower()
            if key not in _TRACKING_PARAMS:
                query_parts.append(part)
    query = "&".join(sorted(query_parts))
    return urlunparse((parsed.scheme or "https", host, path, "", query, ""))


def same_registrable_domain(a: str, b: str) -> bool:
    ha = urlparse(a).netloc.lower().split(":")[0]
    hb = urlparse(b).netloc.lower().split(":")[0]
    if ha == hb:
        return True
    return ha.endswith(f".{hb}") or hb.endswith(f".{ha}")


@dataclass
class CrawlFrontier:
    seed_url: str
    max_depth: int = 2
    max_urls: int = 30
    include_patterns: list[str] = field(default_factory=list)
    exclude_patterns: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.seed_url = normalize_url(self.seed_url)
        self._seen: set[str] = set()
        self._queue: deque[tuple[str, int]] = deque()
        self._queue.append((self.seed_url, 0))
        self._seen.add(self.seed_url)

    def _matches(self, url: str) -> bool:
        if self.include_patterns:
            if not any(re.search(p, url, re.I) for p in self.include_patterns):
                return False
        if self.exclude_patterns:
            if any(re.search(p, url, re.I) for p in self.exclude_patterns):
                return False
        return True

    def add_links(self, base_url: str, links: list[str]) -> None:
        depth = self._current_depth(base_url)
        if depth >= self.max_depth:
            return
        for link in links:
            if len(self._seen) >= self.max_urls:
                return
            norm = normalize_url(link, base_url)
            if norm in self._seen:
                continue
            if not same_registrable_domain(self.seed_url, norm):
                continue
            if not self._matches(norm):
                continue
            self._seen.add(norm)
            self._queue.append((norm, depth + 1))

    def _current_depth(self, url: str) -> int:
        norm = normalize_url(url)
        for u, d in self._queue:
            if u == norm:
                return d
        return self.max_depth

    def pop(self) -> tuple[str, int] | None:
        if not self._queue:
            return None
        return self._queue.popleft()

    def pending_count(self) -> int:
        return len(self._queue)

    def to_checkpoint(self) -> dict:
        return {
            "seed_url": self.seed_url,
            "max_depth": self.max_depth,
            "queue": list(self._queue),
            "seen": list(self._seen),
        }

    @classmethod
    def from_checkpoint(cls, data: dict) -> CrawlFrontier:
        frontier = cls(
            seed_url=data["seed_url"],
            max_depth=data.get("max_depth", 2),
            max_urls=len(data.get("seen", [])) + len(data.get("queue", [])) + 10,
        )
        frontier._seen = set(data.get("seen", []))
        frontier._queue = deque(tuple(x) for x in data.get("queue", []))
        return frontier
