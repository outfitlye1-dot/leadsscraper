from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.database.database import get_db
from app.models.user import User
from app.schemas.whatsapp_chat import (
    WhatsAppChatContact,
    WhatsAppChatManualOutboundRequest,
    WhatsAppChatOpenerResponse,
    WhatsAppChatReplyRequest,
    WhatsAppChatReplyResponse,
    WhatsAppChatThreadResponse,
    WhatsAppCloudSendRequest,
    WhatsAppCloudSendResponse,
    WhatsAppCloudStatusResponse,
)
from app.services.whatsapp_chat_service import WhatsAppChatService
from app.services.whatsapp_cloud_service import WhatsAppCloudService

router = APIRouter(prefix="/api/whatsapp-chat", tags=["whatsapp-chat"])


@router.get("/cloud/status", response_model=WhatsAppCloudStatusResponse)
def whatsapp_cloud_status(
    current_user: User = Depends(get_current_user),
) -> WhatsAppCloudStatusResponse:
    return WhatsAppCloudStatusResponse(**WhatsAppCloudService().status())


@router.get("/contacts", response_model=list[WhatsAppChatContact])
def list_whatsapp_contacts(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[WhatsAppChatContact]:
    return WhatsAppChatService(db).list_contacts(current_user)


@router.get("/{lead_id}", response_model=WhatsAppChatThreadResponse)
def get_whatsapp_thread(
    lead_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WhatsAppChatThreadResponse:
    return WhatsAppChatService(db).get_thread(current_user, lead_id)


@router.post("/{lead_id}/reply", response_model=WhatsAppChatReplyResponse)
def reply_whatsapp_chat(
    lead_id: int,
    data: WhatsAppChatReplyRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WhatsAppChatReplyResponse:
    return WhatsAppChatService(db).reply(
        current_user,
        lead_id,
        data.customer_message,
        hint=data.hint,
    )


@router.post("/{lead_id}/outbound", response_model=WhatsAppChatOpenerResponse)
def save_manual_outbound(
    lead_id: int,
    data: WhatsAppChatManualOutboundRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WhatsAppChatOpenerResponse:
    return WhatsAppChatService(db).save_manual_outbound(current_user, lead_id, data.body)


@router.post("/{lead_id}/opener", response_model=WhatsAppChatOpenerResponse)
def draft_whatsapp_opener(
    lead_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WhatsAppChatOpenerResponse:
    return WhatsAppChatService(db).draft_opener(current_user, lead_id)


@router.post("/{lead_id}/send", response_model=WhatsAppCloudSendResponse)
def send_whatsapp_cloud(
    lead_id: int,
    data: WhatsAppCloudSendRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WhatsAppCloudSendResponse:
    return WhatsAppChatService(db).send_via_cloud(
        current_user,
        lead_id,
        body=data.body,
        message_id=data.message_id,
        mode=data.mode,
        template_name=data.template_name,
        language_code=data.language_code,
    )


@router.delete("/{lead_id}")
def clear_whatsapp_thread(
    lead_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    return WhatsAppChatService(db).clear_thread(current_user, lead_id)
