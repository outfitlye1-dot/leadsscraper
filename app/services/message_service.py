from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.campaign import MessageType
from app.models.user import User
from app.repositories.campaign_repository import CampaignRepository
from app.repositories.cv_repository import CVRepository
from app.repositories.lead_repository import LeadRepository
from app.repositories.message_repository import MessageRepository
from app.schemas.message import MessageGenerateRequest, MessageGenerateResponse
from app.services.groq_service import GroqService


class MessageService:
    def __init__(self, db: Session):
        self.lead_repository = LeadRepository(db)
        self.cv_repository = CVRepository(db)
        self.campaign_repository = CampaignRepository(db)
        self.message_repository = MessageRepository(db)
        self.groq_service = GroqService(db)

    def generate_message(self, user: User, data: MessageGenerateRequest) -> MessageGenerateResponse:
        self.groq_service.user_id = user.id
        lead = self.lead_repository.get_by_id(user.id, data.lead_id)
        if not lead:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")

        cv = self.cv_repository.get_latest_by_user(user.id)
        if not cv:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="CV profile required. Please upload a CV first.",
            )

        if data.campaign_id:
            campaign = self.campaign_repository.get_by_id(user.id, data.campaign_id)
            if not campaign:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Campaign not found",
                )

        display_message, stored_content = self.groq_service.generate_message(
            lead, cv, data.message_type
        )

        self.message_repository.create(
            user.id,
            {
                "lead_id": lead.id,
                "campaign_id": data.campaign_id,
                "message_type": data.message_type,
                "message_content": stored_content,
            },
        )

        return MessageGenerateResponse(message=display_message)
