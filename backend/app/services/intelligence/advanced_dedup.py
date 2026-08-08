"""Enhanced duplicate detection — phone, website, name, address similarity."""

from __future__ import annotations

import re
from difflib import SequenceMatcher

from app.utils.lead_dedup import build_existing_key_index, is_duplicate_of_existing, lead_match_keys


def _normalize_name(name: str) -> str:
    name = name.lower().strip()
    name = re.sub(r"[^a-z0-9\s]", "", name)
    return re.sub(r"\s+", " ", name)


def _name_similar(a: str, b: str) -> bool:
    if not a or not b:
        return False
    na, nb = _normalize_name(a), _normalize_name(b)
    if na == nb:
        return True
    if len(na) >= 4 and len(nb) >= 4:
        return SequenceMatcher(None, na, nb).ratio() >= 0.88
    return False


def _address_similar(a: str | None, b: str | None) -> bool:
    if not a or not b:
        return False
    na = re.sub(r"[^a-z0-9]", "", a.lower())
    nb = re.sub(r"[^a-z0-9]", "", b.lower())
    if len(na) < 8 or len(nb) < 8:
        return False
    return SequenceMatcher(None, na, nb).ratio() >= 0.85


def is_fuzzy_duplicate(lead: dict, existing_lead) -> bool:
    if is_duplicate_of_existing(lead, lead_match_keys(existing_lead)):
        return True
    if _name_similar(lead.get("company_name", ""), getattr(existing_lead, "company_name", "")):
        if lead.get("city") and existing_lead.city and lead["city"].lower() == existing_lead.city.lower():
            return True
    if _address_similar(lead.get("address"), getattr(existing_lead, "address", None)):
        return True
    return False


def mark_batch_duplicates(leads: list[dict], existing_leads: list) -> tuple[list[dict], int]:
    """Flag in-batch and DB duplicates; returns leads with _duplicate_risk and removed count."""
    existing_keys = build_existing_key_index(existing_leads)
    seen_keys: set[str] = set()
    unique: list[dict] = []
    removed = 0

    for lead in leads:
        keys = lead_match_keys(lead)
        if is_duplicate_of_existing(lead, existing_keys):
            removed += 1
            continue
        if keys and keys & seen_keys:
            removed += 1
            continue
        for ex in existing_leads:
            if is_fuzzy_duplicate(lead, ex):
                lead["_duplicate_risk"] = True
                break
        unique.append(lead)
        seen_keys.update(keys)
        existing_keys.update(keys)

    return unique, removed
