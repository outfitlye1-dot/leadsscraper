"""High-accuracy phone extraction — tagged sources for confidence scoring."""

from __future__ import annotations

import re

from bs4 import BeautifulSoup

from app.utils.contact_utils import (
    TEL_HREF_PATTERN,
    WHATSAPP_LABEL_PATTERN,
    _add_phone_candidate,
    extract_phone_from_whatsapp_href,
    pick_best_phone,
)
from app.utils.phone_confidence import PhoneHit, aggregate_phone_hits

ITEMPROP_TEL_PATTERN = re.compile(
    r'itemprop=["\']telephone["\'][^>]*>([^<]{6,30})<',
    re.IGNORECASE,
)


def _hit(raw: str, source: str, country: str | None, *, from_whatsapp: bool = False) -> PhoneHit | None:
    hit = PhoneHit(raw=raw, source=source, country=country, from_whatsapp=from_whatsapp)
    return hit if hit.resolved_e164() else None


def extract_phone_hits_from_html(html: str, country: str | None = None) -> list[PhoneHit]:
    if not html:
        return []

    hits: list[PhoneHit] = []
    soup = BeautifulSoup(html, "lxml")
    raw_html = str(soup)

    for anchor in soup.find_all("a", href=True):
        href = anchor.get("href") or ""
        href_lower = href.lower()
        if any(
            token in href_lower
            for token in ("wa.me", "whatsapp.com", "api.whatsapp.com", "web.whatsapp.com", "whatsapp://")
        ):
            digits = extract_phone_from_whatsapp_href(href)
            if digits:
                h = _hit(digits, "wa_me", country, from_whatsapp=True)
                if h:
                    hits.append(h)
        elif href_lower.startswith("tel:"):
            tel = href.replace("tel:", "").strip()
            if tel:
                h = _hit(tel, "tel_link", country)
                if h:
                    hits.append(h)

    for attr in ("data-href", "data-whatsapp"):
        for node in soup.find_all(attrs={attr: True}):
            value = (node.get(attr) or "").strip()
            if not value:
                continue
            if "whatsapp" in value.lower() or "wa.me" in value.lower():
                digits = extract_phone_from_whatsapp_href(value)
                if digits:
                    h = _hit(digits, "whatsapp_widget", country, from_whatsapp=True)
                    if h:
                        hits.append(h)

    for node in soup.find_all(attrs={"itemprop": re.compile(r"telephone", re.I)}):
        text = node.get_text(strip=True) or node.get("content") or ""
        if text:
            h = _hit(text.replace("tel:", ""), "itemprop", country)
            if h:
                hits.append(h)

    for match in ITEMPROP_TEL_PATTERN.findall(raw_html):
        h = _hit(match, "itemprop", country)
        if h:
            hits.append(h)

    for node in soup.find_all(class_=re.compile(r"whatsapp", re.I)):
        for anchor in node.find_all("a", href=True):
            digits = extract_phone_from_whatsapp_href(anchor["href"])
            if digits:
                h = _hit(digits, "whatsapp_widget", country, from_whatsapp=True)
                if h:
                    hits.append(h)

    for match in TEL_HREF_PATTERN.findall(raw_html):
        h = _hit(match, "tel_link", country)
        if h:
            hits.append(h)

    text = soup.get_text(" ", strip=True)
    for match in WHATSAPP_LABEL_PATTERN.findall(text):
        h = _hit(match, "whatsapp_label", country)
        if h:
            hits.append(h)

    if not hits and text and country:
        from app.utils.contact_utils import (
            _extract_country_mobile_patterns,
            _extract_libphonenumber_matches,
        )

        pattern_candidates: list[str] = []
        _extract_country_mobile_patterns(text, country, pattern_candidates)
        for phone in pattern_candidates:
            h = _hit(phone, "visible_pattern", country)
            if h:
                hits.append(h)

        lib_candidates: list[str] = []
        _extract_libphonenumber_matches(text, country, lib_candidates)
        for phone in lib_candidates:
            if phone not in pattern_candidates:
                h = _hit(phone, "libphonenumber", country)
                if h:
                    hits.append(h)

    return hits


def extract_phones_from_html(html: str, country: str | None = None) -> list[str]:
    verified = pick_verified_phone_from_html(html, country)
    return [verified] if verified else []


def pick_verified_phone_from_html(html: str, country: str | None = None) -> str | None:
    return aggregate_phone_hits(extract_phone_hits_from_html(html, country), country)


def pick_best_phone_from_html(html: str, country: str | None = None) -> str | None:
    return pick_verified_phone_from_html(html, country)
