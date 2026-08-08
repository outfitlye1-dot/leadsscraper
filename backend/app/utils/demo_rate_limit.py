"""In-memory rate limit for public landing-page demo scrapes."""

from __future__ import annotations

import time
from collections import defaultdict

DEMO_MAX_REQUESTS = 5
DEMO_WINDOW_SECONDS = 3600

_hits: dict[str, list[float]] = defaultdict(list)


def allow_demo_request(client_ip: str) -> bool:
    now = time.time()
    window_start = now - DEMO_WINDOW_SECONDS
    recent = [t for t in _hits[client_ip] if t > window_start]
    if len(recent) >= DEMO_MAX_REQUESTS:
        _hits[client_ip] = recent
        return False
    recent.append(now)
    _hits[client_ip] = recent
    return True
