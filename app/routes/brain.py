from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.database.database import get_db
from app.models.user import User
from app.schemas.brain import BrainGenerateResponse, BrainProfileResponse, BrainUpdateRequest
from app.services.brain_service import BrainService

router = APIRouter(prefix="/api/brain", tags=["brain"])


@router.get(
    "",
    response_model=BrainProfileResponse | None,
    summary="Get AI brain profile",
    responses={401: {"description": "Not authenticated"}},
)
def get_brain(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BrainProfileResponse | None:
    return BrainService(db).get_brain(current_user)


@router.put(
    "",
    response_model=BrainProfileResponse,
    summary="Save AI brain profile",
    responses={401: {"description": "Not authenticated"}},
)
def update_brain(
    data: BrainUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BrainProfileResponse:
    return BrainService(db).update_brain(current_user, data)


@router.post(
    "/import-cv",
    response_model=BrainProfileResponse,
    summary="Import CV data into brain",
    responses={
        400: {"description": "No CV uploaded"},
        401: {"description": "Not authenticated"},
    },
)
def import_cv_to_brain(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BrainProfileResponse:
    return BrainService(db).import_from_cv(current_user)


@router.post(
    "/generate",
    response_model=BrainGenerateResponse,
    summary="Generate AI brain system prompt",
    responses={
        400: {"description": "Brain data missing"},
        401: {"description": "Not authenticated"},
    },
)
def generate_brain(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BrainGenerateResponse:
    return BrainService(db).generate_brain(current_user)
