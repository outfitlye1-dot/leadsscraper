from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.database.database import get_db
from app.models.campaign import MessageType
from app.models.user import User
from app.schemas.message import MessageBulkDeleteResponse, MessageListResponse, MessageResponse
from app.services.dashboard_service import MessageHistoryService

router = APIRouter(prefix="/api/messages", tags=["messages"])


@router.get(
    "",
    response_model=MessageListResponse,
    summary="List generated messages",
    description="Retrieve paginated message history with optional filters.",
    responses={401: {"description": "Not authenticated"}},
)
def list_messages(
    lead_id: int | None = Query(None),
    campaign_id: int | None = Query(None),
    message_type: MessageType | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MessageListResponse:
    return MessageHistoryService(db).list_messages(
        current_user, lead_id, campaign_id, message_type, page, page_size
    )


@router.delete(
    "",
    response_model=MessageBulkDeleteResponse,
    status_code=status.HTTP_200_OK,
    summary="Delete messages",
    description="Delete all messages, or only those matching optional filters.",
    responses={401: {"description": "Not authenticated"}},
)
def delete_messages(
    lead_id: int | None = Query(None),
    campaign_id: int | None = Query(None),
    message_type: MessageType | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MessageBulkDeleteResponse:
    return MessageHistoryService(db).delete_messages(
        current_user, lead_id, campaign_id, message_type
    )


@router.get(
    "/{message_id}",
    response_model=MessageResponse,
    summary="Get message by ID",
    description="Retrieve a single generated message by ID.",
    responses={401: {"description": "Not authenticated"}, 404: {"description": "Message not found"}},
)
def get_message(
    message_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MessageResponse:
    return MessageHistoryService(db).get_message(current_user, message_id)
