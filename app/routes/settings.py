from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.database.database import get_db
from app.models.user import User
from app.schemas.common import LeadDatabaseStatsResponse
from app.services.lead_database_service import LeadDatabaseService

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get(
    "/database",
    response_model=LeadDatabaseStatsResponse,
    summary="Lead database stats (background + totals)",
)
def get_lead_database_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> LeadDatabaseStatsResponse:
    return LeadDatabaseService(db).get_stats(current_user)
