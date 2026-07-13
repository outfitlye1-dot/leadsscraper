import csv
from datetime import UTC, datetime
from pathlib import Path

from app.core.config import get_settings
from app.models.lead import Lead
from app.utils.file_utils import ensure_directory


LEAD_CSV_FIELDS = [
    "id",
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
    "city",
    "country",
    "category",
    "industry",
    "notes",
    "source",
    "status",
    "quality_score",
    "quality_tier",
    "whatsapp_ready",
    "created_at",
    "updated_at",
]


def export_leads_to_csv(leads: list[Lead], user_id: int) -> Path:
    settings = get_settings()
    export_dir = ensure_directory(settings.EXPORT_DIR)
    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    file_path = export_dir / f"leads_{user_id}_{timestamp}.csv"

    with file_path.open("w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=LEAD_CSV_FIELDS)
        writer.writeheader()
        for lead in leads:
            writer.writerow(
                {
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
                    "quality_score": lead.quality_score if lead.quality_score is not None else "",
                    "quality_tier": lead.quality_tier or "",
                    "whatsapp_ready": lead.whatsapp_ready if lead.whatsapp_ready is not None else "",
                    "created_at": lead.created_at.isoformat() if lead.created_at else "",
                    "updated_at": lead.updated_at.isoformat() if lead.updated_at else "",
                }
            )

    return file_path
