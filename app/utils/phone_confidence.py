"""Phone confidence scoring — only save numbers that pass strict verification."""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.utils import phone_lib
from app.utils.contact_utils import (
    _countries_match,
    _digits_only,
    _effective_country_for_phone,
    _infer_country_from_valid_digits,
    _matches_known_whatsapp_format,
    extract_phone_from_whatsapp_href,
    format_whatsapp_display,
    normalize_whatsapp_phone,
)

MIN_PHONE_SAVE_SCORE = 75

SOURCE_BASE_SCORE: dict[str, int] = {
    "wa_me": 100,
    "whatsapp_widget": 98,
    "search_snippet": 95,
    "google_maps": 92,
    "schema_org": 90,
    "tel_link": 85,
    "itemprop": 80,
    "whatsapp_label": 78,
    "visible_pattern": 55,
    "libphonenumber": 40,
}

TRUSTED_SOURCES = frozenset(
    {"wa_me", "whatsapp_widget", "search_snippet", "google_maps", "schema_org"}
)


@dataclass
class PhoneHit:
    raw: str
    source: str
    country: str | None = None
    from_whatsapp: bool = False

    def resolved_e164(self) -> str | None:
        wa_sources = {"wa_me", "whatsapp_widget", "search_snippet"}
        use_wa = self.from_whatsapp or self.source in wa_sources
        if use_wa:
            digits = extract_phone_from_whatsapp_href(self.raw) or _digits_only(self.raw)
            country = _effective_country_for_phone(digits, self.country)
            normalized = normalize_whatsapp_phone(
                digits, country, from_whatsapp_link=True
            )
        else:
            country = _effective_country_for_phone(self.raw, self.country)
            normalized = normalize_whatsapp_phone(self.raw, country)
        if not normalized:
            return None
        return f"+{normalized}"


def score_phone_hit(hit: PhoneHit, search_country: str | None) -> int:
    e164 = hit.resolved_e164()
    if not e164 or not phone_lib.is_strict_whatsapp_mobile(e164, search_country):
        return -1

    score = SOURCE_BASE_SCORE.get(hit.source, 35)
    digits = _digits_only(e164)
    inferred = phone_lib.infer_country_from_digits(digits) or _infer_country_from_valid_digits(
        digits
    )

    if search_country and inferred:
        if _countries_match(inferred, search_country):
            score += 15
        elif hit.source in TRUSTED_SOURCES or hit.from_whatsapp:
            pass
        else:
            score -= 55

    if _matches_known_whatsapp_format(digits):
        score += 35

    return score


def _min_required_score(group: list[PhoneHit]) -> int:
    sources = {h.source for h in group}
    if sources & TRUSTED_SOURCES:
        return 70
    if len(group) >= 2:
        return 72
    if sources & {"tel_link", "whatsapp_label", "itemprop"}:
        return 82
    return 95


def aggregate_phone_hits(hits: list[PhoneHit], search_country: str | None) -> str | None:
    """Pick one verified phone from tagged hits; returns None if nothing is trustworthy."""
    groups: dict[str, list[PhoneHit]] = {}
    for hit in hits:
        e164 = hit.resolved_e164()
        if not e164:
            continue
        key = _digits_only(e164)
        groups.setdefault(key, []).append(hit)

    best_e164: str | None = None
    best_total = -1

    for _digits, group in groups.items():
        base = max(score_phone_hit(h, search_country) for h in group)
        if base < 0:
            continue
        consensus_bonus = 30 * (len(group) - 1)
        total = base + consensus_bonus
        min_required = _min_required_score(group)
        if total >= min_required and total > best_total:
            best_total = total
            best_e164 = group[0].resolved_e164()

    if not best_e164:
        return None
    country = search_country or _effective_country_for_phone(best_e164, search_country)
    return format_whatsapp_display(best_e164, country)


def is_trustworthy_phone(
    phone: str | None,
    country: str | None,
    *,
    source: str | None = None,
) -> bool:
    """Final gate before saving a phone on a lead."""
    if not phone:
        return False
    if source == "google_maps":
        return phone_lib.is_strict_whatsapp_mobile(phone, country)

    hit = PhoneHit(raw=phone, source=source or "libphonenumber", country=country)
    return score_phone_hit(hit, country) >= _min_required_score([hit])
