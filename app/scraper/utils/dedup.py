"""Multi-key lead deduplication: email, website host, phone."""

from __future__ import annotations

import re
from urllib.parse import urlparse

from app.utils.contact_utils import normalize_whatsapp_phone
from app.utils.scrape_sources import merge_lead_records


def _host(url: str | None) -> str:
    if not url:
        return ""
    try:
        host = urlparse(url if "://" in url else f"https://{url}").netloc.lower()
        return host[4:] if host.startswith("www.") else host
    except Exception:
        return ""


def _norm_email(email: str | None) -> str:
    return (email or "").strip().lower()


def _norm_phone(phone: str | None, country: str | None) -> str:
    normalized = normalize_whatsapp_phone(phone, country)
    return normalized or re.sub(r"\D", "", phone or "")


def dedupe_leads_production(leads: list[dict]) -> list[dict]:
    by_key: dict[str, dict] = {}

    for lead in leads:
        keys: list[str] = []
        website = lead.get("website")
        email = _norm_email(lead.get("email"))
        phone = _norm_phone(lead.get("phone"), lead.get("country"))
        host = _host(website)
        company = (lead.get("company_name") or "").lower().strip()

        if host:
            keys.append(f"web:{host}")
        if email:
            keys.append(f"email:{email}")
        if phone and len(phone) >= 10:
            keys.append(f"phone:{phone}")
        if company and not keys:
            keys.append(f"name:{company}")

        if not keys:
            continue

        primary = keys[0]
        existing_key = None
        for key in keys:
            if key in by_key:
                existing_key = key
                break

        if existing_key:
            old_ref = by_key[existing_key]
            merged = merge_lead_records(old_ref, lead)
            for k, v in list(by_key.items()):
                if v is old_ref:
                    by_key[k] = merged
            for key in keys:
                by_key[key] = merged
        else:
            by_key[primary] = lead
            for key in keys[1:]:
                by_key[key] = lead

    seen_ids: set[int] = set()
    unique: list[dict] = []
    for lead in by_key.values():
        lid = id(lead)
        if lid in seen_ids:
            continue
        seen_ids.add(lid)
        unique.append(lead)
    return unique
