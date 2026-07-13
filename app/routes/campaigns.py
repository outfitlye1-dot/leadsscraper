from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.database.database import get_db
from app.models.user import User
from app.schemas.message import (
    CampaignCreateRequest,
    CampaignListResponse,
    CampaignResponse,
    CampaignRunRequest,
    CampaignRunResponse,
    CampaignUpdateRequest,
)
from app.services.campaign_service import CampaignService

router = APIRouter(prefix="/api/campaigns", tags=["campaigns"])


@router.post(
    "",
    response_model=CampaignListResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a campaign",
    description="Create a new outreach campaign.",
    responses={401: {"description": "Not authenticated"}, 422: {"description": "Validation error"}},
)
def create_campaign(
    data: CampaignCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CampaignListResponse:
    return CampaignService(db).create_campaign(current_user, data)


@router.get(
    "",
    response_model=list[CampaignListResponse],
    summary="List campaigns",
    description="Retrieve all campaigns with message counts and eligible leads.",
    responses={401: {"description": "Not authenticated"}},
)
def list_campaigns(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[CampaignListResponse]:
    return CampaignService(db).list_campaigns(current_user)


@router.get(
    "/{campaign_id}",
    response_model=CampaignListResponse,
    summary="Get campaign details",
    responses={401: {"description": "Not authenticated"}, 404: {"description": "Not found"}},
)
def get_campaign(
    campaign_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CampaignListResponse:
    return CampaignService(db).get_campaign(current_user, campaign_id)


@router.post(
    "/{campaign_id}/run",
    response_model=CampaignRunResponse,
    summary="Run campaign on leads",
    description="Generate AI messages for leads using this campaign settings.",
    responses={
        400: {"description": "CV missing or campaign completed"},
        401: {"description": "Not authenticated"},
        404: {"description": "Campaign not found"},
    },
)
def run_campaign(
    campaign_id: int,
    data: CampaignRunRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CampaignRunResponse:
    return CampaignService(db).run_campaign(current_user, campaign_id, data)


@router.put(
    "/{campaign_id}",
    response_model=CampaignListResponse,
    summary="Update a campaign",
    description="Update an existing campaign by ID.",
    responses={401: {"description": "Not authenticated"}, 404: {"description": "Campaign not found"}},
)
def update_campaign(
    campaign_id: int,
    data: CampaignUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CampaignListResponse:
    return CampaignService(db).update_campaign(current_user, campaign_id, data)


@router.delete(
    "/{campaign_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a campaign",
    description="Delete a campaign by ID.",
    responses={401: {"description": "Not authenticated"}, 404: {"description": "Campaign not found"}},
)
def delete_campaign(
    campaign_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    CampaignService(db).delete_campaign(current_user, campaign_id)
