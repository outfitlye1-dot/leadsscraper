"""Format scrape metrics for API responses and dashboards."""

from __future__ import annotations

from app.scraper.metrics import ScrapeMetrics


def build_scrape_dashboard(metrics: ScrapeMetrics) -> dict:
    data = metrics.to_dict()
    return {
        "total_pages_scanned": data["pages_fetched"] + data["pages_failed"],
        "total_leads_found": data["leads_parsed"],
        "valid_emails_found": data["valid_emails"],
        "success_rate": data["success_rate"],
        "failed_requests": data["pages_failed"],
        **data,
    }
