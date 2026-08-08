from __future__ import annotations

import logging
import time
from collections.abc import Callable
from typing import TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


def retry_call(
    fn: Callable[[], T],
    *,
    max_attempts: int = 3,
    base_delay: float = 0.5,
    retry_on: tuple[type[Exception], ...] = (Exception,),
    label: str = "operation",
) -> T | None:
    last_exc: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            return fn()
        except retry_on as exc:
            last_exc = exc
            if attempt >= max_attempts:
                logger.warning("%s failed after %s attempts: %s", label, max_attempts, exc)
                break
            delay = base_delay * (2 ** (attempt - 1))
            logger.debug("%s attempt %s failed, retry in %.1fs: %s", label, attempt, delay, exc)
            time.sleep(delay)
    if last_exc:
        raise last_exc
    return None
