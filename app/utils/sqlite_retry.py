"""Retry helpers for SQLite lock contention during concurrent scrape/API access."""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import TypeVar

from sqlalchemy.exc import OperationalError

T = TypeVar("T")


def is_sqlite_locked_error(exc: BaseException) -> bool:
    message = str(exc).lower()
    return "database is locked" in message or "locked" in message


def with_sqlite_retry(
    fn: Callable[[], T],
    *,
    retries: int = 5,
    base_delay: float = 0.05,
) -> T:
    last_error: OperationalError | None = None
    for attempt in range(retries):
        try:
            return fn()
        except OperationalError as exc:
            last_error = exc
            if not is_sqlite_locked_error(exc) or attempt >= retries - 1:
                raise
            time.sleep(base_delay * (2**attempt))
    if last_error:
        raise last_error
    raise RuntimeError("sqlite retry failed")
