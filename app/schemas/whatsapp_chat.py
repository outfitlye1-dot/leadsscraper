from datetime import datetime

from pydantic import BaseModel, Field


class WhatsAppChatContact(BaseModel):
    lead_id: int
    company_name: str | None = None
    contact_name: str | None = None
    phone: str
    city: str | None = None
    country: str | None = None
    last_message: str | None = None
    last_message_at: datetime | None = None
    message_count: int = 0


class WhatsAppChatMessageOut(BaseModel):
    id: int
    lead_id: int
    direction: str
    body: str
    created_at: datetime


class WhatsAppChatThreadResponse(BaseModel):
    lead_id: int
    company_name: str | None = None
    contact_name: str | None = None
    phone: str
    city: str | None = None
    country: str | None = None
    memory_summary: str | None = None
    last_price_quoted: float | None = None
    customer_budget: float | None = None
    deal_status: str | None = None
    messages: list[WhatsAppChatMessageOut] = Field(default_factory=list)


class WhatsAppChatReplyRequest(BaseModel):
    customer_message: str = Field(..., min_length=1, max_length=4000)
    hint: str | None = Field(None, max_length=500)


class WhatsAppChatManualOutboundRequest(BaseModel):
    body: str = Field(..., min_length=1, max_length=4000)


class WhatsAppChatReplyResponse(BaseModel):
    customer: WhatsAppChatMessageOut
    reply: WhatsAppChatMessageOut


class WhatsAppChatOpenerResponse(BaseModel):
    reply: WhatsAppChatMessageOut


class WhatsAppCloudStatusResponse(BaseModel):
    configured: bool
    phone_number_id: str | None = None
    business_account_id: str | None = None
    display_number: str | None = None
    api_version: str | None = None


class WhatsAppCloudSendRequest(BaseModel):
    body: str | None = Field(None, max_length=4096)
    message_id: int | None = None
    # text (default) or template
    mode: str = Field("text", pattern="^(text|template)$")
    template_name: str | None = Field(None, max_length=120)
    language_code: str = "en_US"


class WhatsAppCloudSendResponse(BaseModel):
    success: bool
    message_id: str | None = None
    to: str | None = None
    local_message_id: int | None = None
    detail: str | None = None
