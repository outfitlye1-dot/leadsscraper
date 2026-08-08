"""Social media intelligence — activity signals from URLs and crawl hints."""

from __future__ import annotations

from urllib.parse import urlparse


def analyze_social_presence(lead: dict) -> dict:
    score = 0
    verified = False
    platforms: list[str] = []

    fb = lead.get("facebook_url")
    ig = lead.get("instagram_url")
    li = lead.get("linkedin_url")

    if fb and _is_valid_social_url(fb, ("facebook.com", "fb.com")):
        score += 25
        platforms.append("facebook")
        verified = True
    if ig and _is_valid_social_url(ig, ("instagram.com",)):
        score += 30
        platforms.append("instagram")
        verified = True
    if li and _is_valid_social_url(li, ("linkedin.com",)):
        score += 20
        platforms.append("linkedin")
        verified = True

    meta = dict(lead.get("intelligence_meta") or {})
    crawl = str(meta.get("crawl_description", "")).lower()
    if any(h in crawl for h in ("instagram", "follow us", "facebook", "social")):
        score += 15
        meta["social_active_hint"] = True

    if lead.get("is_running_ads"):
        score += 20

    lead["social_activity_score"] = min(100, score)
    lead["social_links_verified"] = verified
    meta["social_platforms"] = platforms
    lead["intelligence_meta"] = meta
    return lead


def _is_valid_social_url(url: str, hosts: tuple[str, ...]) -> bool:
    try:
        host = urlparse(url if "://" in url else f"https://{url}").netloc.lower()
        return any(h in host for h in hosts)
    except Exception:
        return False
