from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.campaign import CampaignStatus, MessageType
from app.models.lead import Lead, LeadStatus
from app.models.user import User
from app.repositories.campaign_repository import CampaignRepository
from app.repositories.cv_repository import CVRepository
from app.repositories.lead_repository import LeadRepository
from app.repositories.message_repository import MessageRepository
from app.schemas.message import (
    CampaignCreateRequest,
    CampaignListResponse,
    CampaignResponse,
    CampaignRunRequest,
    CampaignRunResponse,
    CampaignRunResultItem,
    CampaignUpdateRequest,
)
from app.services.groq_service import GroqService
from app.utils.contact_utils import build_whatsapp_link


def _lead_has_contact_for_type(lead: Lead, message_type: MessageType) -> bool:
    if message_type == MessageType.whatsapp:
        return bool(lead.phone and lead.phone.strip())
    if message_type == MessageType.email:
        return bool(lead.email and lead.email.strip())
    if message_type == MessageType.linkedin:
        return bool(lead.linkedin_url and lead.linkedin_url.strip()) or bool(lead.company_name)
    return bool(lead.phone or lead.email)


class CampaignService:
    def __init__(self, db: Session):
        self.campaign_repository = CampaignRepository(db)
        self.db = db
        self.lead_repository = LeadRepository(db)
        self.message_repository = MessageRepository(db)
        self.cv_repository = CVRepository(db)
        self.groq_service = GroqService(db)

    def _eligible_leads_count(self, user_id: int, message_type: MessageType) -> int:
        leads = self.lead_repository.list_for_campaign_run(user_id, limit=500)
        return sum(1 for lead in leads if _lead_has_contact_for_type(lead, message_type))

    def _to_list_response(self, campaign, user_id: int) -> CampaignListResponse:
        base = CampaignResponse.model_validate(campaign)
        return CampaignListResponse(
            **base.model_dump(),
            message_count=self.message_repository.count_by_campaign(user_id, campaign.id),
            eligible_leads=self._eligible_leads_count(user_id, campaign.message_type),
        )

    def create_campaign(self, user: User, data: CampaignCreateRequest) -> CampaignListResponse:
        campaign = self.campaign_repository.create(user.id, data.model_dump())
        return self._to_list_response(campaign, user.id)

    def list_campaigns(self, user: User) -> list[CampaignListResponse]:
        campaigns = self.campaign_repository.get_all(user.id)
        return [self._to_list_response(c, user.id) for c in campaigns]

    def get_campaign(self, user: User, campaign_id: int) -> CampaignListResponse:
        campaign = self.campaign_repository.get_by_id(user.id, campaign_id)
        if not campaign:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")
        return self._to_list_response(campaign, user.id)

    def update_campaign(
        self, user: User, campaign_id: int, data: CampaignUpdateRequest
    ) -> CampaignListResponse:
        campaign = self.campaign_repository.get_by_id(user.id, campaign_id)
        if not campaign:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found"
            )
        updated = self.campaign_repository.update(
            campaign, data.model_dump(exclude_unset=True)
        )
        return self._to_list_response(updated, user.id)

    def delete_campaign(self, user: User, campaign_id: int) -> None:
        campaign = self.campaign_repository.get_by_id(user.id, campaign_id)
        if not campaign:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found"
            )
        self.campaign_repository.delete(campaign)

    def run_campaign(
        self, user: User, campaign_id: int, data: CampaignRunRequest
    ) -> CampaignRunResponse:
        self.groq_service.user_id = user.id
        campaign = self.campaign_repository.get_by_id(user.id, campaign_id)
        if not campaign:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")

        if campaign.status == CampaignStatus.completed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Campaign already completed. Create a new campaign or change status to draft/active.",
            )

        cv = self.cv_repository.get_latest_by_user(user.id)
        if not cv:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="CV profile required. Upload CV first for AI messages.",
            )

        lead_status = None
        if data.lead_status:
            try:
                lead_status = LeadStatus(data.lead_status)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid lead status: {data.lead_status}",
                )

        leads = self.lead_repository.list_for_campaign_run(
            user.id,
            status=lead_status,
            lead_ids=data.lead_ids,
            limit=data.limit * 3,
        )

        results: list[CampaignRunResultItem] = []
        generated = 0
        skipped = 0
        failed = 0
        processed = 0

        for lead in leads:
            if generated >= data.limit:
                break

            processed += 1

            if not _lead_has_contact_for_type(lead, campaign.message_type):
                skipped += 1
                results.append(
                    CampaignRunResultItem(
                        lead_id=lead.id,
                        company_name=lead.company_name,
                        success=False,
                        error=f"No contact for {campaign.message_type.value}",
                    )
                )
                continue

            if data.skip_existing and self.message_repository.exists_for_lead_campaign(
                user.id, lead.id, campaign.id
            ):
                skipped += 1
                results.append(
                    CampaignRunResultItem(
                        lead_id=lead.id,
                        company_name=lead.company_name,
                        success=False,
                        error="Already messaged in this campaign",
                    )
                )
                continue

            try:
                display_message, stored_content = self.groq_service.generate_message(
                    lead, cv, campaign.message_type
                )
                self.message_repository.create(
                    user.id,
                    {
                        "lead_id": lead.id,
                        "campaign_id": campaign.id,
                        "message_type": campaign.message_type,
                        "message_content": stored_content,
                    },
                )
                whatsapp_url = None
                if campaign.message_type == MessageType.whatsapp and lead.phone:
                    whatsapp_url = build_whatsapp_link(lead.phone, display_message)

                if lead.status == LeadStatus.new:
                    self.lead_repository.update(lead, {"status": LeadStatus.contacted})

                generated += 1
                results.append(
                    CampaignRunResultItem(
                        lead_id=lead.id,
                        company_name=lead.company_name,
                        success=True,
                        message_preview=display_message,
                        whatsapp_url=whatsapp_url,
                    )
                )
            except HTTPException as exc:
                failed += 1
                results.append(
                    CampaignRunResultItem(
                        lead_id=lead.id,
                        company_name=lead.company_name,
                        success=False,
                        error=str(exc.detail),
                    )
                )
            except Exception as exc:
                failed += 1
                results.append(
                    CampaignRunResultItem(
                        lead_id=lead.id,
                        company_name=lead.company_name,
                        success=False,
                        error=str(exc),
                    )
                )

        if generated > 0 and campaign.status == CampaignStatus.draft:
            self.campaign_repository.update(campaign, {"status": CampaignStatus.active})
        elif campaign.status != CampaignStatus.paused:
            self.campaign_repository.update(campaign, {"status": CampaignStatus.active})

        self.db.refresh(campaign)

        return CampaignRunResponse(
            campaign_id=campaign.id,
            campaign_status=campaign.status,
            processed=processed,
            generated=generated,
            skipped=skipped,
            failed=failed,
            results=results,
        )
