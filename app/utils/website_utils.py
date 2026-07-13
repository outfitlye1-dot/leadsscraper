import re
from enum import Enum

SOCIAL_ONLY_HOSTS = (
    "facebook.com",
    "fb.com",
    "instagram.com",
    "twitter.com",
    "x.com",
    "tiktok.com",
    "youtube.com",
    "linkedin.com",
)

MAPS_HOSTS = (
    "google.com",
    "google.com.pk",
    "goo.gl",
    "maps.app.goo.gl",
)


class WebsiteFilter(str, Enum):
    all = "all"
    with_website = "with_website"
    without_website = "without_website"


def _host(url: str) -> str:
    cleaned = url.strip().lower()
    if cleaned.startswith("http://"):
        cleaned = cleaned[7:]
    elif cleaned.startswith("https://"):
        cleaned = cleaned[8:]
    if cleaned.startswith("www."):
        cleaned = cleaned[4:]
    return cleaned.split("/")[0].split("?")[0]


def is_google_maps_url(url: str | None) -> bool:
    if not url:
        return False
    host = _host(url)
    return any(maps in host for maps in MAPS_HOSTS) or "/maps/" in url.lower()


def is_social_only_url(url: str | None) -> bool:
    if not url:
        return False
    host = _host(url)
    return any(social in host for social in SOCIAL_ONLY_HOSTS)


def has_real_website(url: str | None) -> bool:
    if not url or not url.strip():
        return False
    if is_google_maps_url(url):
        return False
    if is_social_only_url(url):
        return False
    host = _host(url)
    return "." in host and len(host) > 3


def normalize_website_field(lead_data: dict) -> dict:
    """Classify website vs no-website; strip fake URLs (Google Maps, social-only)."""
    data = dict(lead_data)
    website = data.get("website")
    maps_url = None

    if website and is_google_maps_url(website):
        maps_url = website
        website = None

    if website and is_social_only_url(website):
        host = _host(website)
        if "facebook" in host and not data.get("facebook_url"):
            data["facebook_url"] = website
        elif "instagram" in host and not data.get("instagram_url"):
            data["instagram_url"] = website
        elif "linkedin" in host and not data.get("linkedin_url"):
            data["linkedin_url"] = website
        website = None

    data["website"] = website if has_real_website(website) else None
    data["has_website"] = bool(data["website"])

    note_parts = []
    if data["has_website"]:
        note_parts.append("Website: Yes")
    else:
        note_parts.append("Website: No — offer website build")

    if data.get("instagram_url"):
        note_parts.append("Instagram: Yes")
    else:
        note_parts.append("Instagram: No — offer online presence")

    if maps_url:
        note_parts.append(f"Google Maps: {maps_url}")

    existing = data.get("notes") or ""
    tag_line = f"[{'; '.join(note_parts)}]"
    data["notes"] = f"{existing}\n{tag_line}".strip() if existing else tag_line

    data.pop("has_website", None)
    return data


def apply_website_filter(
    leads_data: list[dict], website_filter: WebsiteFilter
) -> list[dict]:
    if website_filter == WebsiteFilter.all:
        return leads_data

    filtered: list[dict] = []
    for lead in leads_data:
        has_site = has_real_website(lead.get("website"))
        if website_filter == WebsiteFilter.with_website and has_site:
            filtered.append(lead)
        elif website_filter == WebsiteFilter.without_website and not has_site:
            filtered.append(lead)
    return filtered
