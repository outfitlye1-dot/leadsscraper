from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.database.database import get_db
from app.models.user import User
from app.schemas.common import DashboardStatsResponse
from app.services.dashboard_service import DashboardService

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get(
    "/stats",
    response_model=DashboardStatsResponse,
    summary="Get dashboard analytics",
    description="Return lead, campaign, and message statistics for the authenticated user.",
    responses={401: {"description": "Not authenticated"}},
)
def get_dashboard_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DashboardStatsResponse:
    return DashboardService(db).get_stats(current_user)
