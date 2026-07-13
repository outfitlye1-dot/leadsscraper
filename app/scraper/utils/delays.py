import random
import time


def random_delay(min_ms: int | None = None, max_ms: int | None = None) -> None:
    if min_ms is None or max_ms is None:
        from app.core.config import get_settings

        settings = get_settings()
        min_ms = settings.SCRAPER_DELAY_MIN_MS if min_ms is None else min_ms
        max_ms = settings.SCRAPER_DELAY_MAX_MS if max_ms is None else max_ms
    time.sleep(random.uniform(min_ms / 1000, max_ms / 1000))
