"""Meta Ads intelligence enrichment."""

from __future__ import annotations


def enrich_meta_ad_lead(lead: dict, item: dict | None = None) -> dict:
    item = item or {}
    platforms = item.get("platforms") or item.get("publisher_platforms") or []
    if isinstance(platforms, list):
        ad_platform = ",".join(str(p) for p in platforms[:4]) or "facebook"
    else:
        ad_platform = str(platforms) if platforms else "facebook"

    ads_count = item.get("ads_count") or item.get("adCount") or 1
    try:
        ads_count = max(1, int(ads_count))
    except (TypeError, ValueError):
        ads_count = 1

    score = 55
    if lead.get("website"):
        score += 20
    if item.get("is_active", True):
        score += 15
    if lead.get("instagram_url"):
        score += 10
    score = min(100, score + min(ads_count, 5) * 3)

    lead["is_running_ads"] = True
    lead["ads_count"] = ads_count
    lead["ad_platform"] = ad_platform[:50]
    landing = lead.get("website") or item.get("landingUrl") or item.get("link_url")
    lead["landing_page"] = str(landing)[:500] if landing else None
    lead["ad_activity_score"] = score
    return lead
