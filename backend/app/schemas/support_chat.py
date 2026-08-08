from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class SupportMessageCreate(BaseModel):
    body: str = Field(..., min_length=1, max_length=8000)


class SupportMessageResponse(BaseModel):
    id: int
    direction: Literal["outbound", "inbound"]
    body_text: str
    sent_at: datetime
    sender_name: str
    sender_role: str
    sender_user_id: int


class SupportThreadResponse(BaseModel):
    user_id: int
    user_name: str
    user_email: str
    user_avatar_url: str | None = None
    last_message_at: datetime | None = None
    last_preview: str | None = None
    unread_count: int = 0


class SupportThreadDetailResponse(BaseModel):
    user_id: int
    user_name: str
    user_email: str
    user_avatar_url: str | None = None
    messages: list[SupportMessageResponse]
    unread_count: int = 0


class SupportMessageDeleteResponse(BaseModel):
    success: bool = True
    message: str = "Message deleted"
