"""Per-domain request throttling."""

from __future__ import annotations

import threading
import time
from urllib.parse import urlparse

_lock = threading.Lock()
_last_request: dict[str, float] = {}
_min_interval = 0.12


def set_min_interval(seconds: float) -> None:
    global _min_interval
    _min_interval = max(0.05, seconds)


def _host(url: str) -> str:
    return urlparse(url).netloc.lower().split(":")[0]


def wait_for_domain(url: str) -> None:
    host = _host(url)
    if not host:
        return
    wait = 0.0
    with _lock:
        now = time.monotonic()
        last = _last_request.get(host, 0.0)
        wait = _min_interval - (now - last)
        if wait <= 0:
            _last_request[host] = now
            return
    # Sleep OUTSIDE the lock — previously this serialized every crawl worker
    time.sleep(wait)
    with _lock:
        _last_request[host] = time.monotonic()


def reset_throttle() -> None:
    with _lock:
        _last_request.clear()
