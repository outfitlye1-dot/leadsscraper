from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.auth import get_current_admin, get_current_user
from app.database.database import get_db
from app.models.user import User
from app.schemas.support_chat import (
    SupportMessageCreate,
    SupportMessageDeleteResponse,
    SupportMessageResponse,
    SupportThreadDetailResponse,
    SupportThreadResponse,
)
from app.services.support_chat_service import SupportChatService

router = APIRouter(prefix="/api/support", tags=["support"])


@router.get("/thread", response_model=SupportThreadDetailResponse)
def get_my_support_thread(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SupportThreadDetailResponse:
    detail = SupportChatService(db).get_thread_detail(current_user)
    return SupportThreadDetailResponse(**detail)


@router.post("/messages", response_model=SupportMessageResponse)
def send_my_support_message(
    data: SupportMessageCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SupportMessageResponse:
    message = SupportChatService(db).send_message(current_user, data.body)
    return SupportMessageResponse(**message)


@router.get("/admin/threads", response_model=list[SupportThreadResponse])
def list_admin_support_threads(
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> list[SupportThreadResponse]:
    threads = SupportChatService(db).list_threads_for_admin()
    return [SupportThreadResponse(**thread) for thread in threads]


@router.get("/admin/threads/{user_id}", response_model=SupportThreadDetailResponse)
def get_admin_support_thread(
    user_id: int,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> SupportThreadDetailResponse:
    detail = SupportChatService(db).get_thread_detail(current_admin, user_id)
    return SupportThreadDetailResponse(**detail)


@router.post("/admin/threads/{user_id}/messages", response_model=SupportMessageResponse)
def send_admin_support_message(
    user_id: int,
    data: SupportMessageCreate,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> SupportMessageResponse:
    message = SupportChatService(db).send_message(
        current_admin, data.body, target_user_id=user_id
    )
    return SupportMessageResponse(**message)


@router.delete("/messages/{message_id}", response_model=SupportMessageDeleteResponse)
def delete_my_support_message(
    message_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SupportMessageDeleteResponse:
    SupportChatService(db).delete_message(current_user, message_id)
    return SupportMessageDeleteResponse()
