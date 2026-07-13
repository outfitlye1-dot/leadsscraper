"""Lead database stats for Settings → Database page."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.user import User
from app.repositories.lead_repository import LeadRepository
from app.schemas.common import LeadDatabaseStatsResponse, LeadDatabaseSummaryItem
from app.services.background_scrape_store import background_scrape_store


def _database_name(database_url: str) -> str:
    if database_url.startswith("sqlite"):
        raw = database_url.split("///", 1)[-1] if "///" in database_url else database_url.split("//", 1)[-1]
        return Path(raw).name or "leadgen.db"
    tail = database_url.rsplit("/", 1)[-1]
    return tail.split("?")[0] or "database"


def _database_size_bytes(database_url: str) -> int | None:
    if not database_url.startswith("sqlite"):
        return None
    raw = database_url.split("///", 1)[-1] if "///" in database_url else database_url.split("//", 1)[-1]
    path = Path(raw)
    if not path.is_absolute():
        from app.core.config import BASE_DIR

        path = BASE_DIR / path
    if path.is_file():
        return path.stat().st_size
    return None


class LeadDatabaseService:
    def __init__(self, db: Session):
        self.db = db
        self.lead_repository = LeadRepository(db)

    def get_stats(self, user: User) -> LeadDatabaseStatsResponse:
        settings = get_settings()
        db_url = settings.DATABASE_URL
        bg = background_scrape_store.get_status(user.id)
        recent = self.lead_repository.list_recent_background_leads(user.id, limit=8)

        return LeadDatabaseStatsResponse(
            database_name=_database_name(db_url),
            database_type="SQLite" if db_url.startswith("sqlite") else "PostgreSQL",
            database_size_bytes=_database_size_bytes(db_url),
            total_leads=self.lead_repository.count_total(user.id),
            inbox_leads=self.lead_repository.count_inbox(user.id),
            saved_leads=self.lead_repository.count_saved(user.id),
            background_leads=self.lead_repository.count_background_leads(user.id),
            manual_leads=max(
                0,
                self.lead_repository.count_total(user.id)
                - self.lead_repository.count_background_leads(user.id),
            ),
            with_phone=self.lead_repository.count_with_phone(user.id),
            without_website=self.lead_repository.count_without_website(user.id),
            background_active=bg["active"],
            background_running=bg["running"],
            background_total_saved=bg["total_saved"],
            background_iteration=bg["iteration"],
            background_last_query=bg["last_query"],
            recent_background=[
                LeadDatabaseSummaryItem(
                    id=lead.id,
                    company_name=lead.company_name,
                    phone=lead.phone,
                    city=lead.city,
                    country=lead.country,
                    created_at=lead.created_at.isoformat(),
                    keyword=(
                        (lead.intelligence_meta or {})
                        .get("scrape_context", {})
                        .get("keyword")
                    ),
                    location=(
                        (lead.intelligence_meta or {})
                        .get("scrape_context", {})
                        .get("location")
                    ),
                )
                for lead in recent
            ],
        )
