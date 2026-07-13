from datetime import datetime

from fastapi import APIRouter, Depends, File, Query, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.database.database import get_db
from app.models.lead import LeadStatus
from app.models.user import User
from app.schemas.lead import (
    LeadBulkDeleteRequest,
    LeadBulkSaveRequest,
    LeadCreateRequest,
    LeadImportResponse,
    LeadIntelligenceResponse,
    LeadListResponse,
    LeadQualificationResponse,
    LeadResponse,
    LeadUpdateRequest,
    LeadWebsiteAuditResponse,
)
from app.services.lead_service import LeadFilterParams, LeadService

router = APIRouter(prefix="/api/leads", tags=["leads"])


def _filters(
    q: str | None = Query(None, description="Search company, contact, phone, email, website"),
    city: str | None = Query(None),
    country: str | None = Query(None),
    industry: str | None = Query(None),
    source: str | None = Query(None),
    quality_tier: str | None = Query(None, pattern="^(high|medium|low)$"),
    status: LeadStatus | None = Query(None),
    whatsapp_ready: bool | None = Query(None),
    has_email: bool | None = Query(None),
    has_website: bool | None = Query(None),
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    saved: bool | None = Query(False, description="True=saved leads only, False=inbox only"),
) -> LeadFilterParams:
    return LeadFilterParams(
        q=q,
        city=city,
        country=country,
        industry=industry,
        source=source,
        quality_tier=quality_tier,
        status=status,
        whatsapp_ready=whatsapp_ready,
        has_email=has_email,
        has_website=has_website,
        date_from=date_from,
        date_to=date_to,
        saved=saved,
    )


@router.post(
    "",
    response_model=LeadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new lead",
)
def create_lead(
    data: LeadCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> LeadResponse:
    return LeadService(db).create_lead(current_user, data)


@router.get("", response_model=LeadListResponse, summary="List leads with search and filters")
def list_leads(
    filters: LeadFilterParams = Depends(_filters),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> LeadListResponse:
    return LeadService(db).list_leads(current_user, filters, page, page_size)


@router.post("/import", response_model=LeadImportResponse, summary="Import leads from CSV")
def import_leads(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> LeadImportResponse:
    return LeadService(db).import_leads_csv(current_user, file)


@router.get("/export", summary="Export leads to CSV or Excel")
def export_leads(
    ids: str | None = Query(None, description="Comma-separated lead IDs to export"),
    format: str = Query("csv", pattern="^(csv|xlsx)$"),
    filters: LeadFilterParams = Depends(_filters),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FileResponse:
    service = LeadService(db)
    lead_ids = None
    if ids:
        lead_ids = [int(i.strip()) for i in ids.split(",") if i.strip()]
    else:
        all_leads, _ = service.lead_repository.search(
            user_id=current_user.id,
            page=1,
            page_size=10000,
            **filters.as_dict(),
        )
        lead_ids = [lead.id for lead in all_leads]

    file_path = service.export_leads(current_user, lead_ids, fmt=format)
    media_type = (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        if format == "xlsx"
        else "text/csv"
    )
    ext = "xlsx" if format == "xlsx" else "csv"
    return FileResponse(
        path=str(file_path),
        filename=f"leads_export.{ext}",
        media_type=media_type,
    )


@router.post("/bulk-delete", status_code=status.HTTP_200_OK, summary="Bulk delete leads")
def bulk_delete_leads(
    data: LeadBulkDeleteRequest,
    filters: LeadFilterParams = Depends(_filters),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    deleted = LeadService(db).bulk_delete_leads(current_user, data, filters)
    return {"deleted": deleted}


@router.post("/bulk-save", status_code=status.HTTP_200_OK, summary="Save leads to Saved list")
def bulk_save_leads(
    data: LeadBulkSaveRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    saved = LeadService(db).bulk_save_leads(current_user, data)
    return {"saved": saved}


@router.post(
    "/cleanup-no-contact",
    status_code=status.HTTP_200_OK,
    summary="Delete inbox leads without a phone number",
)
def cleanup_leads_without_contact(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    return LeadService(db).cleanup_inbox_leads_without_contact(current_user)


@router.post(
    "/save-with-contact",
    status_code=status.HTTP_200_OK,
    summary="Save inbox leads that have phone or email",
)
def save_leads_with_contact(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    return LeadService(db).save_inbox_leads_with_contact(current_user)


@router.get(
    "/{lead_id}/intelligence",
    response_model=LeadIntelligenceResponse,
    summary="Full lead intelligence profile",
)
def get_lead_intelligence(
    lead_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> LeadIntelligenceResponse:
    return LeadService(db).get_lead_intelligence(current_user, lead_id)


@router.get(
    "/{lead_id}/website-audit",
    response_model=LeadWebsiteAuditResponse,
    summary="Website opportunity audit for a lead",
)
def get_website_audit(
    lead_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> LeadWebsiteAuditResponse:
    return LeadService(db).get_website_audit(current_user, lead_id)


@router.get(
    "/{lead_id}/qualification",
    response_model=LeadQualificationResponse,
    summary="AI/rule-based qualification result for a lead",
)
def get_qualification(
    lead_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> LeadQualificationResponse:
    return LeadService(db).get_qualification(current_user, lead_id)


@router.get("/{lead_id}", response_model=LeadResponse, summary="Get lead by ID")
def get_lead(
    lead_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> LeadResponse:
    return LeadService(db).get_lead(current_user, lead_id)


@router.put("/{lead_id}", response_model=LeadResponse, summary="Update a lead")
def update_lead(
    lead_id: int,
    data: LeadUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> LeadResponse:
    return LeadService(db).update_lead(current_user, lead_id, data)


@router.delete("/{lead_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete a lead")
def delete_lead(
    lead_id: int,
    saved: bool = Query(False, description="Set true when deleting from Saved page"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    service = LeadService(db)
    if saved:
        service.delete_saved_lead(current_user, lead_id)
    else:
        service.delete_lead(current_user, lead_id)


@router.post("/{lead_id}/save", response_model=LeadResponse, summary="Save lead to Saved list")
def save_lead(
    lead_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> LeadResponse:
    return LeadService(db).save_lead(current_user, lead_id)


@router.post("/{lead_id}/unsave", response_model=LeadResponse, summary="Move lead back to inbox")
def unsave_lead(
    lead_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> LeadResponse:
    return LeadService(db).unsave_lead(current_user, lead_id)
