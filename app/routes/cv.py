from fastapi import APIRouter, Depends, File, UploadFile, status
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.database.database import get_db
from app.models.user import User
from app.schemas.cv import CVProfileResponse, CVRawResponse, CVUploadResponse
from app.services.cv_service import CVService

router = APIRouter(prefix="/api/cv", tags=["cv"])


@router.post(
    "/upload",
    response_model=CVUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload CV",
    description="Upload a PDF or DOCX CV, extract text, and generate AI profile.",
    responses={
        400: {"description": "Invalid file or extraction failed"},
        401: {"description": "Not authenticated"},
    },
)
async def upload_cv(
    file: UploadFile = File(..., description="CV file (PDF or DOCX)"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CVUploadResponse:
    return await CVService(db).upload_cv(current_user, file)


@router.get(
    "/profile",
    response_model=CVProfileResponse | None,
    summary="Get CV profile",
    description="Get the authenticated user's latest CV profile with AI summaries.",
    responses={401: {"description": "Not authenticated"}},
)
def get_cv_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CVProfileResponse | None:
    return CVService(db).get_profile(current_user)


@router.get(
    "/raw",
    response_model=CVRawResponse,
    summary="Get raw CV text",
    description="Get the raw extracted text from the user's latest CV upload.",
    responses={401: {"description": "Not authenticated"}, 404: {"description": "No CV found"}},
)
def get_cv_raw(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CVRawResponse:
    return CVService(db).get_raw_text(current_user)
