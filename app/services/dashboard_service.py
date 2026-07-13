import math

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.campaign import MessageType
from app.models.lead import LeadStatus
from app.models.user import User
from app.repositories.campaign_repository import CampaignRepository
from app.repositories.lead_repository import LeadRepository
from app.repositories.message_repository import MessageRepository
from app.schemas.common import DashboardStatsResponse
from app.schemas.message import MessageBulkDeleteResponse, MessageListResponse, MessageResponse


class DashboardService:
    def __init__(self, db: Session):
        self.lead_repository = LeadRepository(db)
        self.campaign_repository = CampaignRepository(db)
        self.message_repository = MessageRepository(db)

    def get_stats(self, user: User) -> DashboardStatsResponse:
        return DashboardStatsResponse(
            total_leads=self.lead_repository.count_dashboard_total(user.id),
            new_leads=self.lead_repository.count_dashboard_by_status(user.id, LeadStatus.new),
            contacted_leads=self.lead_repository.count_dashboard_by_status(
                user.id, LeadStatus.contacted
            ),
            interested_leads=self.lead_repository.count_dashboard_by_status(
                user.id, LeadStatus.interested
            ),
            follow_up_leads=self.lead_repository.count_dashboard_by_status(
                user.id, LeadStatus.follow_up
            ),
            closed_leads=self.lead_repository.count_dashboard_by_status(user.id, LeadStatus.closed),
            lost_leads=self.lead_repository.count_dashboard_by_status(user.id, LeadStatus.lost),
            campaign_count=self.campaign_repository.count_by_user(user.id),
            messages_generated=self.message_repository.count_by_user(user.id),
        )


class MessageHistoryService:
    def __init__(self, db: Session):
        self.message_repository = MessageRepository(db)

    def get_message(self, user: User, message_id: int) -> MessageResponse:
        message = self.message_repository.get_by_id(user.id, message_id)
        if not message:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Message not found"
            )
        return MessageResponse.model_validate(message)

    def list_messages(
        self,
        user: User,
        lead_id: int | None = None,
        campaign_id: int | None = None,
        message_type: MessageType | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> MessageListResponse:
        page_size = min(page_size, 100)
        messages, total = self.message_repository.search(
            user_id=user.id,
            lead_id=lead_id,
            campaign_id=campaign_id,
            message_type=message_type,
            page=page,
            page_size=page_size,
        )
        pages = math.ceil(total / page_size) if total > 0 else 0
        return MessageListResponse(
            items=[MessageResponse.model_validate(m) for m in messages],
            total=total,
            page=page,
            page_size=page_size,
            pages=pages,
        )

    def delete_messages(
        self,
        user: User,
        lead_id: int | None = None,
        campaign_id: int | None = None,
        message_type: MessageType | None = None,
    ) -> MessageBulkDeleteResponse:
        deleted = self.message_repository.delete_matching(
            user.id,
            lead_id=lead_id,
            campaign_id=campaign_id,
            message_type=message_type,
        )
        if deleted == 0:
            return MessageBulkDeleteResponse(deleted=0, message="No messages to delete.")
        scope = "matching your filters" if any([lead_id, campaign_id, message_type]) else ""
        return MessageBulkDeleteResponse(
            deleted=deleted,
            message=f"Deleted {deleted} message(s){f' {scope}' if scope else ''}.",
        )
