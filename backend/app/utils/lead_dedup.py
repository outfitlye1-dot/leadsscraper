"""Match scraped leads against existing database records."""

from __future__ import annotations

import re
from urllib.parse import urlparse

from app.models.lead import Lead
from app.utils.contact_utils import normalize_whatsapp_phone


def _host(url: str | None) -> str:
    if not url:
        return ""
    try:
        host = urlparse(url if "://" in url else f"https://{url}").netloc.lower()
        return host[4:] if host.startswith("www.") else host
    except Exception:
        return ""


def lead_match_keys(lead: dict | Lead) -> set[str]:
    """Build dedupe keys for a lead dict or ORM model."""
    keys: set[str] = set()

    if isinstance(lead, Lead):
        email = (lead.email or "").strip().lower()
        phone = normalize_whatsapp_phone(lead.phone, lead.country) or re.sub(
            r"\D", "", lead.phone or ""
        )
        website = lead.website
        company = (lead.company_name or "").lower().strip()
        country = lead.country
    elif isinstance(lead, dict):
        email = (lead.get("email") or "").strip().lower()
        phone = normalize_whatsapp_phone(lead.get("phone"), lead.get("country")) or re.sub(
            r"\D", "", lead.get("phone") or ""
        )
        website = lead.get("website")
        company = (lead.get("company_name") or "").lower().strip()
        country = lead.get("country")
    else:
        email = (getattr(lead, "email", None) or "").strip().lower()
        phone = normalize_whatsapp_phone(getattr(lead, "phone", None), getattr(lead, "country", None)) or re.sub(
            r"\D", "", getattr(lead, "phone", None) or ""
        )
        website = getattr(lead, "website", None)
        company = (getattr(lead, "company_name", None) or "").lower().strip()
        country = getattr(lead, "country", None)

    host = _host(website)
    if host:
        keys.add(f"web:{host}")
    if email:
        keys.add(f"email:{email}")
    if phone and len(phone) >= 10:
        keys.add(f"phone:{phone}")
    if company and len(company) >= 3:
        keys.add(f"name:{company}|{(country or '').lower()}")

    return keys


def build_existing_key_index(existing_leads: list[Lead]) -> set[str]:
    index: set[str] = set()
    for lead in existing_leads:
        index.update(lead_match_keys(lead))
    return index


def is_duplicate_of_existing(lead: dict, existing_keys: set[str]) -> bool:
    keys = lead_match_keys(lead)
    if not keys:
        return False
    return bool(keys & existing_keys)


def filter_new_leads(
    leads_data: list[dict], existing_leads: list[Lead]
) -> tuple[list[dict], int]:
    """Return only leads that don't match existing DB records."""
    existing_keys = build_existing_key_index(existing_leads)
    new_leads: list[dict] = []
    skipped = 0
    seen_new: set[str] = set()

    for lead in leads_data:
        if is_duplicate_of_existing(lead, existing_keys):
            skipped += 1
            continue
        keys = lead_match_keys(lead)
        if keys and keys & seen_new:
            skipped += 1
            continue
        new_leads.append(lead)
        seen_new.update(keys)
        existing_keys.update(keys)

    return new_leads, skipped
