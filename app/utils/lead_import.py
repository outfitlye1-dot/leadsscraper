import csv
import io
from typing import Any

from app.models.lead import LeadStatus
from app.scraper.validators.quality import apply_quality_to_lead


IMPORT_FIELDS = {
    "company_name",
    "contact_name",
    "phone",
    "email",
    "website",
    "linkedin_url",
    "facebook_url",
    "instagram_url",
    "address",
    "postal_code",
    "category",
    "city",
    "country",
    "industry",
    "notes",
    "source",
    "status",
}


def _normalize_row(row: dict[str, Any]) -> dict[str, Any] | None:
    company = (row.get("company_name") or row.get("company") or row.get("name") or "").strip()
    if not company:
        return None

    data: dict[str, Any] = {"company_name": company, "source": "csv_import"}
    for field in IMPORT_FIELDS:
        if field == "company_name":
            continue
        value = row.get(field)
        if value is not None and str(value).strip():
            data[field] = str(value).strip()

    status_raw = (data.get("status") or "new").lower().replace(" ", "_")
    try:
        data["status"] = LeadStatus(status_raw)
    except ValueError:
        data["status"] = LeadStatus.new

    return apply_quality_to_lead(data)


def parse_leads_csv(content: bytes) -> list[dict]:
    text = content.decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        return []

    normalized_fieldnames = [name.strip().lower().replace(" ", "_") for name in reader.fieldnames]
    leads: list[dict] = []
    for raw_row in reader:
        row = {
            normalized_fieldnames[i]: (value or "").strip()
            for i, value in enumerate(raw_row.values())
            if i < len(normalized_fieldnames)
        }
        parsed = _normalize_row(row)
        if parsed:
            leads.append(parsed)
    return leads
