"""Website opportunity audit — detects digital gaps local businesses have."""

from __future__ import annotations

import json
import re
from urllib.parse import urlparse

from app.utils.website_utils import has_real_website, is_social_only_url


def _has_mobile_viewport(html: str) -> bool:
    return bool(re.search(r'name=["\']viewport["\']', html, re.I))


def _has_contact_form(html: str) -> bool:
    lower = html.lower()
    if "<form" not in lower:
        return False
    return any(
        token in lower
        for token in ('type="email"', "type='email'", 'name="email"', "mailto:", "contact")
    )


def _has_booking_system(html: str, text: str) -> bool:
    combined = f"{html} {text}".lower()
    hints = (
        "book now",
        "book appointment",
        "reservation",
        "calendly",
        "acuity",
        "setmore",
        "fresha",
        "simplybook",
        "opentable",
    )
    return any(h in combined for h in hints)


def _has_pricing_or_services(html: str, text: str) -> bool:
    combined = f"{html} {text}".lower()
    path_hints = ("/pricing", "/services", "/menu", "/packages", "/rates")
    text_hints = ("our services", "pricing", "menu", "packages", "rates")
    return any(h in combined for h in path_hints + text_hints)


def _seo_metadata_score(soup) -> tuple[int, list[str]]:
    problems: list[str] = []
    score = 0
    title = soup.find("title")
    if title and title.get_text(strip=True):
        score += 15
    else:
        problems.append("Missing page title")
    desc = soup.find("meta", attrs={"name": re.compile("^description$", re.I)})
    if desc and desc.get("content", "").strip():
        score += 15
    else:
        problems.append("Missing meta description")
    og = soup.find("meta", property="og:title")
    if og and og.get("content"):
        score += 10
    return score, problems


def _old_website_indicators(html: str, text: str) -> list[str]:
    problems: list[str] = []
    if re.search(r"<table[^>]+width", html, re.I):
        problems.append("Outdated table-based layout")
    year_match = re.search(r"copyright[^\d]*(\d{4})", text, re.I)
    if year_match:
        try:
            if int(year_match.group(1)) < 2018:
                problems.append("Outdated copyright year")
        except ValueError:
            pass
    if html.count("<font") > 2 or html.count("<center") > 2:
        problems.append("Legacy HTML styling")
    return problems


def audit_website_from_html(
    lead: dict,
    html: str | None = None,
    *,
    fetch_ok: bool = True,
    load_time_ms: int | None = None,
) -> dict:
    """Return lead dict enriched with website_quality_score, website_problems, website_opportunity_score."""
    website = lead.get("website")
    problems: list[str] = []
    opportunity = 0
    quality = 50

    if not website or not has_real_website(website):
        if is_social_only_url(website or ""):
            problems.append("Social-only presence (no real website)")
        else:
            problems.append("No website")
        lead["website_quality_score"] = 0
        lead["website_opportunity_score"] = 90
        lead["website_problems"] = problems
        meta = dict(lead.get("intelligence_meta") or {})
        meta["no_real_website"] = True
        meta["website_audit_label"] = "None" if not website else "Social only"
        lead["intelligence_meta"] = meta
        return lead

    parsed = urlparse(website if "://" in website else f"https://{website}")
    if parsed.scheme != "https":
        problems.append("Missing HTTPS")
        opportunity += 15
        quality -= 20
    else:
        quality += 10

    if not html or not fetch_ok:
        problems.append("Website unreachable or broken")
        quality = min(quality, 25)
        opportunity += 25
    else:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "lxml")
        text = soup.get_text(" ", strip=True)[:8000]

        if not _has_mobile_viewport(html):
            problems.append("No mobile optimization")
            opportunity += 20
            quality -= 15

        if load_time_ms and load_time_ms > 4000:
            problems.append("Slow loading website")
            opportunity += 10
            quality -= 10

        if not _has_contact_form(html):
            problems.append("Missing contact form")
            opportunity += 12

        if not _has_booking_system(html, text):
            problems.append("No booking/ordering system detected")
            opportunity += 15

        if not _has_pricing_or_services(html, text):
            problems.append("Missing pricing/services page")
            opportunity += 10

        seo_score, seo_problems = _seo_metadata_score(soup)
        quality += seo_score // 3
        problems.extend(seo_problems)

        problems.extend(_old_website_indicators(html, text))

        meta = dict(lead.get("intelligence_meta") or {})
        meta["crawl_description"] = text[:500]
        meta["pages_crawled"] = meta.get("pages_crawled", []) + ["homepage"]
        lead["intelligence_meta"] = meta

    quality = max(0, min(100, quality))
    opportunity = max(0, min(100, opportunity + max(0, 100 - quality) // 2))

    label = "Poor" if quality < 40 else "Average" if quality < 70 else "Good"
    meta = dict(lead.get("intelligence_meta") or {})
    meta["website_audit_label"] = label
    lead["intelligence_meta"] = meta
    lead["website_quality_score"] = quality
    lead["website_opportunity_score"] = opportunity
    lead["website_problems"] = list(dict.fromkeys(problems))[:15]
    return lead


def audit_website_lightweight(lead: dict) -> dict:
    """Audit without HTML — URL-only checks."""
    return audit_website_from_html(lead, html=None, fetch_ok=False)
