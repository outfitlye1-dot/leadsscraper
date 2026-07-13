import logging

from app.scraper.metrics import ScrapeMetrics

logger = logging.getLogger("scraper.production")


def log_fetch_success(metrics: ScrapeMetrics | None, url: str) -> None:
    if metrics:
        metrics.inc("pages_fetched")
    logger.info("FETCH_OK %s", url)


def log_fetch_failure(metrics: ScrapeMetrics | None, url: str, reason: str) -> None:
    if metrics:
        metrics.inc("pages_failed")
        metrics.add_failed_url(url)
        metrics.add_error(f"fetch:{url}:{reason}")
    logger.warning("FETCH_FAIL %s — %s", url, reason)


def log_lead_parsed(metrics: ScrapeMetrics | None, company: str) -> None:
    if metrics:
        metrics.inc("leads_parsed")
    logger.info("LEAD_OK %s", company)


def log_lead_rejected(metrics: ScrapeMetrics | None, url: str, reason: str) -> None:
    if metrics:
        metrics.inc("leads_rejected")
        metrics.add_error(f"reject:{url}:{reason}")
    logger.debug("LEAD_REJECT %s — %s", url, reason)
