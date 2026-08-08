"""Offline quality report for leads stored in SQLite."""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.utils.contact_utils import is_junk_email, is_valid_email
from app.utils.phone_lib import phone_matches_search_region
from app.utils.scrape_sources import (
    is_directory_or_aggregator_url,
    is_listicle_or_bad_title,
    is_listicle_url,
    title_conflicts_with_location,
)


def _load_leads(db_path: Path) -> list[dict]:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        """
        SELECT company_name, phone, email, website, city, country, source
        FROM leads
        ORDER BY id
        """
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def _location_label(lead: dict) -> str:
    city = (lead.get("city") or "").strip()
    country = (lead.get("country") or "").strip()
    if city and country:
        return f"{city}, {country}"
    return country or city


def audit_leads(leads: list[dict]) -> dict[str, list[str]]:
    issues: dict[str, list[str]] = {
        "directory_url": [],
        "listicle_url": [],
        "bad_title": [],
        "junk_email": [],
        "wrong_region_phone": [],
        "location_title_conflict": [],
    }

    for lead in leads:
        name = lead.get("company_name") or "?"
        location = _location_label(lead)
        website = lead.get("website")

        if is_directory_or_aggregator_url(website):
            issues["directory_url"].append(f"{name} -> {website}")
        if is_listicle_url(website):
            issues["listicle_url"].append(f"{name} -> {website}")
        if is_listicle_or_bad_title(name):
            issues["bad_title"].append(name)
        email = lead.get("email")
        if email and (is_junk_email(email) or not is_valid_email(email)):
            issues["junk_email"].append(f"{name} -> {email}")
        phone = lead.get("phone")
        if phone and location and not phone_matches_search_region(phone, location):
            issues["wrong_region_phone"].append(f"{name} -> {phone} (search: {location})")
        if title_conflicts_with_location(name, location):
            issues["location_title_conflict"].append(f"{name} (search: {location})")

    return issues


def main() -> int:
    db_path = ROOT / "leadgen.db"
    if not db_path.exists():
        print(f"No database at {db_path}")
        return 1

    leads = _load_leads(db_path)
    print(f"Auditing {len(leads)} leads in {db_path.name}\n")

    issues = audit_leads(leads)
    total_flags = 0
    for category, items in issues.items():
        print(f"{category}: {len(items)}")
        for item in items:
            print(f"  - {item}")
        total_flags += len(items)
        print()

    print(f"Total issue flags: {total_flags}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
