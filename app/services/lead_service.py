import logging
import math
import re
from datetime import UTC, datetime

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.models.lead import LeadStatus
from app.models.user import User
from app.repositories.lead_repository import LeadRepository
from app.schemas.lead import (
    LeadBulkDeleteRequest,
    LeadBulkSaveRequest,
    LeadCreateRequest,
    LeadImportResponse,
    LeadListResponse,
    LeadResponse,
    LeadUpdateRequest,
)
from app.scraper.validators.quality import apply_quality_to_lead
from app.services.intelligence.pipeline import LeadIntelligencePipeline
from app.utils.lead_db_fields import strip_lead_dict
from app.utils.contact_links import build_contact_links
from app.utils.csv_export import export_leads_to_csv
from app.utils.lead_dedup import filter_new_leads
from app.utils.lead_import import parse_leads_csv
from app.scraper.storage.exporters import export_leads_to_excel

logger = logging.getLogger(__name__)


class LeadFilterParams:
    def __init__(
        self,
        *,
        q: str | None = None,
        city: str | None = None,
        country: str | None = None,
        industry: str | None = None,
        status: LeadStatus | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        source: str | None = None,
        quality_tier: str | None = None,
        whatsapp_ready: bool | None = None,
        has_email: bool | None = None,
        has_website: bool | None = None,
        saved: bool | None = False,
    ):
        self.q = q
        self.city = city
        self.country = country
        self.industry = industry
        self.status = status
        self.date_from = date_from
        self.date_to = date_to
        self.source = source
        self.quality_tier = quality_tier
        self.whatsapp_ready = whatsapp_ready
        self.has_email = has_email
        self.has_website = has_website
        self.saved = saved

    def as_dict(self) -> dict:
        return {
            "q": self.q,
            "city": self.city,
            "country": self.country,
            "industry": self.industry,
            "status": self.status,
            "date_from": self.date_from,
            "date_to": self.date_to,
            "source": self.source,
            "quality_tier": self.quality_tier,
            "whatsapp_ready": self.whatsapp_ready,
            "has_email": self.has_email,
            "has_website": self.has_website,
            "saved": self.saved,
        }


class LeadService:
    def __init__(self, db: Session):
        self.lead_repository = LeadRepository(db)

    def _to_response(self, lead) -> LeadResponse:
        response = LeadResponse.model_validate(lead)
        return response.model_copy(update={"contact_links": build_contact_links(lead)})

    def create_lead(self, user: User, data: LeadCreateRequest) -> LeadResponse:
        payload = apply_quality_to_lead(data.model_dump())
        if not payload.get("source"):
            payload["source"] = "manual"
        lead = self.lead_repository.create(user.id, payload)
        return self._to_response(lead)

    def get_lead(self, user: User, lead_id: int) -> LeadResponse:
        lead = self.lead_repository.get_by_id(user.id, lead_id)
        if not lead:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")
        return self._to_response(lead)

    def get_lead_intelligence(self, user: User, lead_id: int):
        from app.schemas.lead import (
            LeadIntelligenceResponse,
            LeadQualificationResponse,
            LeadWebsiteAuditResponse,
        )

        lead = self.lead_repository.get_by_id(user.id, lead_id)
        if not lead:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")

        meta = lead.intelligence_meta or {}
        website_audit = LeadWebsiteAuditResponse(
            lead_id=lead.id,
            company_name=lead.company_name,
            website=lead.website,
            website_quality_score=lead.website_quality_score,
            website_opportunity_score=lead.website_opportunity_score,
            website_problems=lead.website_problems,
            audit_label=meta.get("website_audit_label"),
        )
        qualification = LeadQualificationResponse(
            lead_id=lead.id,
            company_name=lead.company_name,
            ai_qualification=lead.ai_qualification,
            recommended_offer=lead.recommended_offer,
            qualification_reason=lead.qualification_reason,
            buying_intent_score=lead.buying_intent_score,
            intent_tier=lead.intent_tier,
            recommended_service=lead.recommended_service,
        )
        return LeadIntelligenceResponse(
            lead_id=lead.id,
            company_name=lead.company_name,
            website_audit=website_audit,
            qualification=qualification,
            contact={
                "phone": lead.phone,
                "email": lead.email,
                "phone_verified": lead.phone_verified,
                "email_verified": lead.email_verified,
                "whatsapp_ready": lead.whatsapp_ready,
            },
            google_maps={
                "reviews_count": lead.reviews_count,
                "rating": lead.rating,
                "business_hours": lead.business_hours,
                "google_profile_score": lead.google_profile_score,
                "photos_count": lead.photos_count,
            },
            social={
                "facebook_url": lead.facebook_url,
                "instagram_url": lead.instagram_url,
                "social_activity_score": lead.social_activity_score,
                "social_links_verified": lead.social_links_verified,
            },
            meta_ads={
                "is_running_ads": lead.is_running_ads,
                "ads_count": lead.ads_count,
                "ad_platform": lead.ad_platform,
                "landing_page": lead.landing_page,
                "ad_activity_score": lead.ad_activity_score,
            },
            niche={
                "niche_key": lead.niche_key,
                "recommended_service": lead.recommended_service,
                "pain_points": meta.get("niche_pain_points"),
            },
            intelligence_meta=meta,
        )

    def get_website_audit(self, user: User, lead_id: int):
        from app.schemas.lead import LeadWebsiteAuditResponse

        lead = self.lead_repository.get_by_id(user.id, lead_id)
        if not lead:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")
        meta = lead.intelligence_meta or {}
        return LeadWebsiteAuditResponse(
            lead_id=lead.id,
            company_name=lead.company_name,
            website=lead.website,
            website_quality_score=lead.website_quality_score,
            website_opportunity_score=lead.website_opportunity_score,
            website_problems=lead.website_problems,
            audit_label=meta.get("website_audit_label"),
        )

    def get_qualification(self, user: User, lead_id: int):
        from app.schemas.lead import LeadQualificationResponse

        lead = self.lead_repository.get_by_id(user.id, lead_id)
        if not lead:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")
        return LeadQualificationResponse(
            lead_id=lead.id,
            company_name=lead.company_name,
            ai_qualification=lead.ai_qualification,
            recommended_offer=lead.recommended_offer,
            qualification_reason=lead.qualification_reason,
            buying_intent_score=lead.buying_intent_score,
            intent_tier=lead.intent_tier,
            recommended_service=lead.recommended_service,
        )

    def update_lead(self, user: User, lead_id: int, data: LeadUpdateRequest) -> LeadResponse:
        lead = self.lead_repository.get_by_id(user.id, lead_id)
        if not lead:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")
        patch = data.model_dump(exclude_unset=True)
        if patch:
            merged = {
                "company_name": lead.company_name,
                "contact_name": lead.contact_name,
                "phone": lead.phone,
                "email": lead.email,
                "website": lead.website,
                "linkedin_url": lead.linkedin_url,
                "facebook_url": lead.facebook_url,
                "instagram_url": lead.instagram_url,
                "address": lead.address,
                "city": lead.city,
                "country": lead.country,
                "industry": lead.industry,
                **patch,
            }
            scored = apply_quality_to_lead(merged)
            patch["quality_score"] = scored["quality_score"]
            patch["quality_tier"] = scored["quality_tier"]
            patch["whatsapp_ready"] = scored["whatsapp_ready"]
        updated = self.lead_repository.update(lead, patch)
        return self._to_response(updated)

    def delete_lead(self, user: User, lead_id: int, *, allow_saved: bool = False) -> None:
        lead = self.lead_repository.get_by_id(user.id, lead_id)
        if not lead:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")
        if lead.is_saved and not allow_saved:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Saved leads cannot be deleted from here. Remove from Saved first.",
            )
        self.lead_repository.delete(lead)

    def save_lead(self, user: User, lead_id: int) -> LeadResponse:
        lead = self.lead_repository.get_by_id(user.id, lead_id)
        if not lead:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")
        if lead.is_saved:
            return self._to_response(lead)
        updated = self.lead_repository.update(
            lead,
            {"is_saved": True, "saved_at": datetime.now(UTC)},
        )
        try:
            from app.services.email_outreach.agent import AiOutreachAgent

            AiOutreachAgent(self.lead_repository.db).on_leads_saved(user.id, [lead_id])
        except Exception:
            logger.exception("Outreach agent hook failed after save for user %s", user.id)
        return self._to_response(updated)

    def unsave_lead(self, user: User, lead_id: int) -> LeadResponse:
        lead = self.lead_repository.get_by_id(user.id, lead_id)
        if not lead:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")
        if not lead.is_saved:
            return self._to_response(lead)
        updated = self.lead_repository.unsave(lead)
        return self._to_response(updated)

    def bulk_save_leads(self, user: User, data: LeadBulkSaveRequest) -> int:
        saved = self.lead_repository.save_by_ids(user.id, data.ids)
        if saved == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No leads to save")
        try:
            from app.services.email_outreach.agent import AiOutreachAgent

            AiOutreachAgent(self.lead_repository.db).on_leads_saved(user.id, data.ids)
        except Exception:
            logger.exception("Outreach agent hook failed after bulk save for user %s", user.id)
        return saved

    def bulk_delete_leads(
        self,
        user: User,
        data: LeadBulkDeleteRequest,
        filters: LeadFilterParams,
    ) -> int:
        if data.select_all:
            deleted = self.lead_repository.delete_matching(user.id, **filters.as_dict())
        elif data.ids:
            deleted = self.lead_repository.delete_by_ids(user.id, data.ids)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Provide lead IDs or set select_all to true",
            )

        if deleted == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No leads to delete")
        return deleted

    def delete_saved_lead(self, user: User, lead_id: int) -> None:
        lead = self.lead_repository.get_by_id(user.id, lead_id)
        if not lead or not lead.is_saved:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Saved lead not found")
        self.lead_repository.delete(lead)

    def list_leads(
        self,
        user: User,
        filters: LeadFilterParams,
        page: int = 1,
        page_size: int = 20,
    ) -> LeadListResponse:
        page_size = min(page_size, 100)
        leads, total = self.lead_repository.search(
            user_id=user.id,
            page=page,
            page_size=page_size,
            **filters.as_dict(),
        )
        pages = math.ceil(total / page_size) if total > 0 else 0
        return LeadListResponse(
            items=[self._to_response(lead) for lead in leads],
            total=total,
            page=page,
            page_size=page_size,
            pages=pages,
        )

    def export_leads(self, user: User, lead_ids: list[int] | None = None, fmt: str = "csv"):
        leads = self.lead_repository.get_all_for_user(user.id, lead_ids)
        if not leads:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No leads to export")
        if fmt == "xlsx":
            return export_leads_to_excel(leads, user.id)
        return export_leads_to_csv(leads, user.id)

    def import_leads_csv(self, user: User, file: UploadFile) -> LeadImportResponse:
        content = file.file.read()
        if not content:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty file")
        try:
            parsed = parse_leads_csv(content)
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid CSV: {exc}",
            ) from exc

        if not parsed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No valid rows found. CSV must include company_name column.",
            )

        existing = self.lead_repository.get_all_for_user_light(user.id)
        new_leads, skipped = filter_new_leads(parsed, existing)
        if new_leads:
            self.lead_repository.bulk_create(user.id, new_leads)

        imported = len(new_leads)
        message = f"Imported {imported} lead(s)"
        if skipped:
            message += f", skipped {skipped} duplicate(s)"
        return LeadImportResponse(imported=imported, skipped_duplicates=skipped, message=message)

    def save_scraped_leads(
        self, user_id: int, leads_data: list[dict], *, search_location: str | None = None
    ) -> tuple[list, int, int, dict]:
        """Filter duplicates, run intelligence pipeline, bulk insert."""
        if not leads_data:
            return [], 0, 0, {}

        leads_data = [apply_quality_to_lead(lead) for lead in leads_data]
        existing = self.lead_repository.get_all_for_user_light(user_id)

        pipeline = LeadIntelligencePipeline(self.lead_repository.db, user_id)
        loc = search_location or (leads_data[0].get("country") if leads_data else None)
        leads_data, intel_stats = pipeline.process_batch(
            leads_data, existing_leads=existing, search_location=loc
        )

        new_leads, skipped = filter_new_leads(leads_data, existing)
        if not new_leads:
            return [], 0, skipped, intel_stats.to_dict()

        new_leads = [strip_lead_dict(lead) for lead in new_leads]
        saved = self.lead_repository.bulk_create(user_id, new_leads)
        return saved, len(saved), skipped, intel_stats.to_dict()

    @staticmethod
    def _lead_has_phone(lead) -> bool:
        phone = getattr(lead, "phone", None)
        if not phone or not str(phone).strip():
            return False
        digits = re.sub(r"\D", "", str(phone))
        return len(digits) >= 10

    @staticmethod
    def _lead_has_email(lead) -> bool:
        email = getattr(lead, "email", None)
        return bool(email and isinstance(email, str) and email.strip())

    @staticmethod
    def _lead_is_email_only(lead) -> bool:
        return LeadService._lead_has_email(lead) and not LeadService._lead_has_phone(lead)

    @staticmethod
    def _lead_should_keep_in_inbox(lead) -> bool:
        """Keep leads with a phone number (email optional). Remove email-only leads."""
        return LeadService._lead_has_phone(lead)

    @staticmethod
    def _lead_has_contact(lead) -> bool:
        return LeadService._lead_should_keep_in_inbox(lead)

    def cleanup_non_phone_leads_by_ids(self, user_id: int, lead_ids: list[int]) -> tuple[int, int]:
        """Delete unsaved inbox leads without phone from a scrape batch; keep others in Leads."""
        if not lead_ids:
            return 0, 0
        leads = self.lead_repository.get_many_by_ids(user_id, lead_ids)
        delete_ids: list[int] = []
        kept = 0
        for lead in leads:
            if lead.is_saved:
                continue
            if self._lead_has_contact(lead):
                kept += 1
            else:
                delete_ids.append(lead.id)
        deleted = 0
        if delete_ids:
            deleted = self.lead_repository.delete_by_ids(user_id, delete_ids, saved=False)
        return kept, deleted

    def save_inbox_leads_with_contact(self, user: User) -> dict[str, int]:
        """Move all unsaved inbox leads with a valid phone number to Saved."""
        leads, _ = self.lead_repository.search(
            user_id=user.id,
            saved=False,
            page=1,
            page_size=100_000,
        )
        save_ids = [lead.id for lead in leads if self._lead_has_contact(lead)]
        saved = self.lead_repository.save_by_ids(user.id, save_ids) if save_ids else 0
        return {"saved": saved}

    def cleanup_inbox_leads_without_contact(self, user: User) -> dict[str, int]:
        """Delete inbox leads without a phone number; keep the rest in Leads."""
        leads, _ = self.lead_repository.search(
            user_id=user.id,
            saved=False,
            page=1,
            page_size=100_000,
        )
        delete_ids = [lead.id for lead in leads if not self._lead_has_phone(lead)]
        deleted = 0
        if delete_ids:
            deleted = self.lead_repository.delete_inbox_by_ids(user.id, delete_ids)
        _, kept = self.lead_repository.search(
            user_id=user.id,
            saved=False,
            page=1,
            page_size=1,
        )
        return {"kept": kept, "deleted": deleted}
