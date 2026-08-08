"""Pydantic schemas for WhatsApp Web automation (separate from Cloud API)."""

from pydantic import BaseModel, Field


class WhatsAppWebStatusResponse(BaseModel):
    enabled: bool
    headless: bool = False
    profile_dir: str = ""
    browser_started: bool = False
    logged_in: bool = False
    worker_running: bool = False
    auto_reply: bool = True
    ignore_groups: bool = True
    owner_user_id: int | None = None
    owner_email: str | None = None
    cdp_mode: bool = False
    cdp_configured: bool = False
    cdp_alive: bool = False
    cloud_api_untouched: bool = True
    message: str | None = None
    daily_outreach_enabled: bool = False
    daily_outreach_limit: int = 5
    daily_outreach_sent_count: int = 0
    daily_outreach_remaining: int = 5
    daily_outreach_interval_minutes: int = 60
    daily_outreach_seconds_until_next: int = 0


class WhatsAppWebQrResponse(BaseModel):
    logged_in: bool
    qr_data_url: str | None = None
    message: str | None = None


class WhatsAppWebReconnectResponse(BaseModel):
    ok: bool = True
    logged_in: bool = False
    profile_dir: str | None = None
    message: str | None = None


class WhatsAppWebStartResponse(BaseModel):
    ok: bool = True
    logged_in: bool = False
    worker_running: bool = False
    qr_data_url: str | None = None
    message: str | None = None
    owner_email: str | None = None


class WhatsAppWebPairCodeRequest(BaseModel):
    phone: str = Field(..., min_length=8, max_length=32)


class WhatsAppWebPairCodeResponse(BaseModel):
    ok: bool = True
    logged_in: bool = False
    pair_code: str | None = None
    phone: str | None = None
    message: str | None = None


class WhatsAppWebLaunchChromeResponse(BaseModel):
    ok: bool = True
    cdp_url: str | None = None
    message: str | None = None
    logged_in: bool = False
    attached: bool = False
    worker_running: bool = False


class WhatsAppWebJobItem(BaseModel):
    id: int
    chat_title: str
    phone_hint: str | None = None
    body: str
    status: str
    ai_replied: bool = False
    reply_body: str | None = None
    error_message: str | None = None
    lead_id: int | None = None
    created_at: str | None = None


class WhatsAppWebSettingsResponse(BaseModel):
    auto_reply: bool = True
    ignore_phones: list[str] = Field(default_factory=list)
    ignore_groups: bool = True
    human_takeover_phones: list[str] = Field(default_factory=list)
    owner_user_id: int | None = None
    owner_email: str | None = None
    daily_outreach_enabled: bool = False
    daily_outreach_limit: int = Field(5, ge=1, le=10)
    daily_outreach_sent_date: str | None = None
    daily_outreach_sent_count: int = 0
    daily_outreach_interval_minutes: int = Field(60, ge=1, le=1440)


class WhatsAppWebSettingsUpdateRequest(BaseModel):
    auto_reply: bool | None = None
    ignore_phones: list[str] | None = None
    ignore_groups: bool | None = None
    human_takeover_phones: list[str] | None = None
    daily_outreach_enabled: bool | None = None
    daily_outreach_limit: int | None = Field(None, ge=1, le=10)
    daily_outreach_interval_minutes: int | None = Field(None, ge=1, le=1440)
