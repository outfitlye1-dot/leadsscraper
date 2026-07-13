from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.auth import get_current_admin
from app.database.database import get_db
from app.models.user import User, UserRole
from app.schemas.admin import (
    AdminDashboardResponse,
    AdminLeadListResponse,
    AdminOutreachSummaryResponse,
    AdminScraperJobListResponse,
    AdminSystemResponse,
    AdminUserCreateRequest,
    AdminUserDetailResponse,
    AdminUserListResponse,
    AdminUserUpdateRequest,
)
from app.schemas.user import UserResponse
from app.services.admin_service import AdminService

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/dashboard", response_model=AdminDashboardResponse)
def admin_dashboard(
    _: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> AdminDashboardResponse:
    return AdminService(db).get_dashboard()


@router.get("/users", response_model=AdminUserListResponse)
def list_users(
    search: str | None = Query(default=None),
    role: UserRole | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    _: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> AdminUserListResponse:
    return AdminService(db).list_users(
        search=search, role=role, page=page, page_size=page_size
    )


@router.get("/users/{user_id}", response_model=AdminUserDetailResponse)
def get_user(
    user_id: int,
    _: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> AdminUserDetailResponse:
    return AdminService(db).get_user(user_id)


@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    data: AdminUserCreateRequest,
    _: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> UserResponse:
    return AdminService(db).create_user(data)


@router.patch("/users/{user_id}", response_model=UserResponse)
def update_user(
    user_id: int,
    data: AdminUserUpdateRequest,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> UserResponse:
    return AdminService(db).update_user(current_user, user_id, data)


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: int,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> None:
    AdminService(db).delete_user(current_user, user_id)


@router.get("/leads", response_model=AdminLeadListResponse)
def list_leads(
    search: str | None = Query(default=None),
    user_id: int | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    _: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> AdminLeadListResponse:
    return AdminService(db).list_leads(
        search=search, user_id=user_id, page=page, page_size=page_size
    )


@router.delete("/leads/{lead_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_lead(
    lead_id: int,
    _: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> None:
    AdminService(db).delete_lead(lead_id)


@router.get("/scraper/jobs", response_model=AdminScraperJobListResponse)
def list_scraper_jobs(
    _: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> AdminScraperJobListResponse:
    return AdminService(db).list_scraper_jobs()


@router.post("/scraper/jobs/{job_id}/cancel", status_code=status.HTTP_204_NO_CONTENT)
def cancel_scraper_job(
    job_id: str,
    _: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> None:
    AdminService(db).cancel_scraper_job(job_id)


@router.get("/outreach/summary", response_model=AdminOutreachSummaryResponse)
def outreach_summary(
    _: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> AdminOutreachSummaryResponse:
    return AdminService(db).outreach_summary()


@router.get("/system", response_model=AdminSystemResponse)
def system_info(
    _: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> AdminSystemResponse:
    return AdminService(db).get_system()
