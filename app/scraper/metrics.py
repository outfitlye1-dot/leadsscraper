from __future__ import annotations

from dataclasses import dataclass, field
from threading import Lock


@dataclass
class ScrapeMetrics:
    """Thread-safe scrape telemetry for dashboards and job responses."""

    pages_discovered: int = 0
    pages_fetched: int = 0
    pages_failed: int = 0
    pages_crawled: int = 0
    requests_per_minute: float = 0.0
    retry_count: int = 0
    browser_renders: int = 0
    js_render_used: int = 0
    images_downloaded: int = 0
    active_workers: int = 0
    queue_size: int = 0
    bot_blocks: int = 0
    proxy_switches: int = 0
    strategy_http: int = 0
    strategy_playwright: int = 0
    strategy_api: int = 0
    leads_parsed: int = 0
    leads_rejected: int = 0
    leads_saved: int = 0
    valid_emails: int = 0
    valid_phones: int = 0
    whatsapp_ready: int = 0
    high_quality: int = 0
    medium_quality: int = 0
    low_quality: int = 0
    validation_errors: list[str] = field(default_factory=list)
    failed_urls: list[str] = field(default_factory=list)

    _lock: Lock = field(default_factory=Lock, repr=False)

    def inc(self, field_name: str, amount: int = 1) -> None:
        with self._lock:
            setattr(self, field_name, getattr(self, field_name) + amount)

    def set(self, field_name: str, value: int | float) -> None:
        with self._lock:
            setattr(self, field_name, value)

    def add_error(self, message: str) -> None:
        with self._lock:
            if len(self.validation_errors) < 100:
                self.validation_errors.append(message)

    def add_failed_url(self, url: str) -> None:
        with self._lock:
            if len(self.failed_urls) < 50:
                self.failed_urls.append(url)

    @property
    def success_rate(self) -> float:
        total = self.pages_fetched + self.pages_failed
        if total == 0:
            return 0.0
        return round(100.0 * self.pages_fetched / total, 1)

    def to_dict(self) -> dict:
        with self._lock:
            return {
                "pages_discovered": self.pages_discovered,
                "pages_fetched": self.pages_fetched,
                "pages_failed": self.pages_failed,
                "pages_crawled": self.pages_crawled,
                "requests_per_minute": self.requests_per_minute,
                "retry_count": self.retry_count,
                "browser_renders": self.browser_renders,
                "js_render_used": self.js_render_used,
                "images_downloaded": self.images_downloaded,
                "active_workers": self.active_workers,
                "queue_size": self.queue_size,
                "bot_blocks": self.bot_blocks,
                "proxy_switches": self.proxy_switches,
                "strategy_http": self.strategy_http,
                "strategy_playwright": self.strategy_playwright,
                "strategy_api": self.strategy_api,
                "leads_parsed": self.leads_parsed,
                "leads_rejected": self.leads_rejected,
                "leads_saved": self.leads_saved,
                "valid_emails": self.valid_emails,
                "valid_phones": self.valid_phones,
                "whatsapp_ready": self.whatsapp_ready,
                "high_quality": self.high_quality,
                "medium_quality": self.medium_quality,
                "low_quality": self.low_quality,
                "success_rate": self.success_rate,
                "validation_errors": list(self.validation_errors[:20]),
                "failed_urls": list(self.failed_urls[:10]),
            }
