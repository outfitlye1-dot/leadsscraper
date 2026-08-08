"""CSV and Excel export helpers."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from app.core.config import get_settings
from app.models.lead import Lead
from app.utils.csv_export import LEAD_CSV_FIELDS, export_leads_to_csv
from app.utils.file_utils import ensure_directory


def export_leads_to_excel(leads: list[Lead], user_id: int) -> Path:
    try:
        from openpyxl import Workbook
    except ImportError as exc:
        raise RuntimeError("openpyxl is required for Excel export. pip install openpyxl") from exc

    settings = get_settings()
    export_dir = ensure_directory(settings.EXPORT_DIR)
    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    file_path = export_dir / f"leads_{user_id}_{timestamp}.xlsx"

    wb = Workbook()
    ws = wb.active
    ws.title = "Leads"
    extra_fields = ["quality_score", "quality_tier", "whatsapp_ready"]
    headers = LEAD_CSV_FIELDS + extra_fields
    ws.append(headers)

    for lead in leads:
        row = {
            "id": lead.id,
            "company_name": lead.company_name,
            "contact_name": lead.contact_name or "",
            "phone": lead.phone or "",
            "email": lead.email or "",
            "website": lead.website or "",
            "linkedin_url": lead.linkedin_url or "",
            "facebook_url": lead.facebook_url or "",
            "instagram_url": lead.instagram_url or "",
            "address": lead.address or "",
            "postal_code": lead.postal_code or "",
            "city": lead.city or "",
            "country": lead.country or "",
            "category": lead.category or "",
            "industry": lead.industry or "",
            "notes": lead.notes or "",
            "source": lead.source or "",
            "status": lead.status.value if lead.status else "",
            "created_at": lead.created_at.isoformat() if lead.created_at else "",
            "updated_at": lead.updated_at.isoformat() if lead.updated_at else "",
            "quality_score": getattr(lead, "quality_score", "") or "",
            "quality_tier": getattr(lead, "quality_tier", "") or "",
            "whatsapp_ready": getattr(lead, "whatsapp_ready", "") or "",
        }
        ws.append([row.get(h, "") for h in headers])

    wb.save(file_path)
    return file_path


def export_leads(leads: list[Lead], user_id: int, fmt: str = "csv") -> Path:
    if fmt == "xlsx":
        return export_leads_to_excel(leads, user_id)
    return export_leads_to_csv(leads, user_id)
