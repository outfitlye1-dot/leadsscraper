"""Pydantic schemas for email outreach API."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class EmailAccountResponse(BaseModel):
    id: int
    provider: str
    email_address: str
    display_name: str | None
    smtp_host: str | None
    smtp_port: int | None
    imap_host: str | None
    imap_port: int | None
    use_tls: bool
    status: str
    is_default: bool
    daily_sent_count: int
    last_sync_at: datetime | None
    last_error: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SmtpAccountCreateRequest(BaseModel):
    email_address: str
    display_name: str | None = None
    password: str = Field(min_length=1)
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    imap_host: str | None = "imap.gmail.com"
    imap_port: int | None = 993
    use_tls: bool = True
    is_default: bool = False


class EmailOutreachSettingsResponse(BaseModel):
    automation_enabled: bool
    auto_send_enabled: bool
    require_review: bool
    daily_send_limit: int
    hourly_send_limit: int
    rate_limit_per_minute: int
    auto_reply_enabled: bool
    auto_reply_simple_only: bool
    include_unsubscribe: bool
    default_email_account_id: int | None
    agent_running: bool = False
    agent_paused: bool = False
    auto_follow_up: bool = True
    working_hours_start: int = 9
    working_hours_end: int = 18
    weekends_enabled: bool = False
    standing_campaign_id: int | None = None
    last_agent_run_at: datetime | None = None
    ai_emails_generated: int = 0
    ai_replies_generated: int = 0
    agent_batch_delay_minutes: int = 10

    model_config = {"from_attributes": True}


class EmailOutreachSettingsUpdateRequest(BaseModel):
    automation_enabled: bool | None = None
    auto_send_enabled: bool | None = None
    require_review: bool | None = None
    daily_send_limit: int | None = Field(default=None, ge=1, le=500)
    hourly_send_limit: int | None = Field(default=None, ge=1, le=100)
    rate_limit_per_minute: int | None = Field(default=None, ge=1, le=30)
    auto_reply_enabled: bool | None = None
    auto_reply_simple_only: bool | None = None
    include_unsubscribe: bool | None = None
    default_email_account_id: int | None = None
    auto_follow_up: bool | None = None
    working_hours_start: int | None = Field(default=None, ge=0, le=23)
    working_hours_end: int | None = Field(default=None, ge=0, le=23)
    weekends_enabled: bool | None = None
    agent_batch_delay_minutes: int | None = Field(default=None, ge=1, le=120)


class FollowUpStepRequest(BaseModel):
    step_number: int = Field(ge=0)
    delay_days: int = Field(ge=0)
    subject_override: str | None = None
    is_active: bool = True


class FollowUpStepResponse(BaseModel):
    id: int
    step_number: int
    delay_days: int
    subject_override: str | None
    is_active: bool

    model_config = {"from_attributes": True}


class EmailOutreachCampaignCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    email_account_id: int | None = None
    campaign_id: int | None = None
    automation_enabled: bool = True
    require_review: bool | None = None
    follow_up_enabled: bool = True
    lead_filter_saved_only: bool = True
    lead_ids: list[int] | None = None
    follow_up_steps: list[FollowUpStepRequest] | None = None


class EmailOutreachCampaignUpdateRequest(BaseModel):
    name: str | None = None
    email_account_id: int | None = None
    status: str | None = None
    automation_enabled: bool | None = None
    require_review: bool | None = None
    follow_up_enabled: bool | None = None
    lead_ids: list[int] | None = None
    follow_up_steps: list[FollowUpStepRequest] | None = None


class EmailOutreachCampaignResponse(BaseModel):
    id: int
    name: str
    campaign_id: int | None
    email_account_id: int | None
    status: str
    automation_enabled: bool
    require_review: bool | None
    follow_up_enabled: bool
    lead_filter_saved_only: bool
    lead_ids: list[int] | None
    stats: dict | None
    follow_up_steps: list[FollowUpStepResponse] = []
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class OutreachEmailResponse(BaseModel):
    id: int
    outreach_campaign_id: int
    lead_id: int
    follow_up_step: int
    to_email: str
    subject: str
    body_text: str
    status: str
    verification_status: str | None
    verification_details: dict | None
    scheduled_at: datetime | None
    sent_at: datetime | None
    opened_at: datetime | None
    replied_at: datetime | None
    error_message: str | None
    ai_generated: bool
    is_follow_up: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class OutreachEmailUpdateRequest(BaseModel):
    subject: str | None = None
    body_text: str | None = None
    status: str | None = None


class EmailVerificationResponse(BaseModel):
    email: str
    is_valid: bool
    is_verified: bool
    is_risky: bool
    is_disposable: bool
    has_mx: bool
    syntax_valid: bool
    domain_valid: bool
    score: int
    reasons: list[str]


class ConversationResponse(BaseModel):
    id: int
    lead_id: int
    outreach_campaign_id: int | None
    subject: str
    status: str
    reply_intent: str | None
    reply_summary: str | None
    follow_ups_stopped: bool
    last_message_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ChatThreadResponse(BaseModel):
    lead_id: int
    conversation_id: int | None = None
    lead_name: str
    lead_email: str = ""
    subject: str
    status: str
    reply_intent: str | None = None
    reply_summary: str | None = None
    last_message_at: datetime | None = None
    last_preview: str | None = None
    has_reply: bool = False
    message_count: int = 0
    unread_count: int = 0
    is_manual_chat: bool = False
    is_online: bool = False
    last_seen_at: datetime | None = None


class ChatMessageResponse(BaseModel):
    id: str
    direction: str
    from_email: str
    to_email: str
    subject: str
    body_text: str
    sent_at: datetime | None = None
    status: str | None = None
    source: str
    outreach_email_id: int | None = None
    delivery_status: str | None = None  # sent | delivered | read


class ChatThreadDetailResponse(BaseModel):
    lead_id: int
    conversation_id: int | None = None
    lead_name: str
    lead_email: str = ""
    subject: str
    status: str
    messages: list[ChatMessageResponse]
    is_online: bool = False
    last_seen_at: datetime | None = None


class ChatReplyRequest(BaseModel):
    subject: str = Field(..., min_length=1, max_length=500)
    body: str = Field("", max_length=20000)
    account_id: int | None = None


class ChatAiReplyRequest(BaseModel):
    """Optional notes for the AI when auto-generating + sending a reply."""

    hint: str | None = Field(None, max_length=500)
    account_id: int | None = None


class ChatStartRequest(BaseModel):
    """Start a WhatsApp-style chat with any Gmail/email address."""

    email: str = Field(..., min_length=3, max_length=255)
    name: str | None = Field(None, max_length=255)
    subject: str = Field("Hello", min_length=1, max_length=500)
    body: str = Field(..., min_length=1, max_length=20000)
    account_id: int | None = None


class AiReplyDraftResponse(BaseModel):
    id: int
    conversation_id: int
    detected_intent: str
    summary: str
    draft_subject: str
    draft_body: str
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class AiReplyDraftActionRequest(BaseModel):
    action: str = Field(pattern="^(approve|reject|edit)$")
    draft_subject: str | None = None
    draft_body: str | None = None


class TimelineEventResponse(BaseModel):
    id: int
    lead_id: int
    event_type: str
    description: str
    event_meta: dict | None
    created_at: datetime

    model_config = {"from_attributes": True}


class EmailOutreachDashboardResponse(BaseModel):
    # Legacy summary
    connected_accounts: int
    active_campaigns: int
    emails_sent: int
    emails_delivered: int
    open_rate: float
    reply_rate: float
    bounce_rate: float
    follow_up_queue: int
    pending_ai_drafts: int
    automation_enabled: bool
    pending_jobs: int
    # Email statistics
    emails_sent_today: int = 0
    emails_sent_this_week: int = 0
    emails_sent_this_month: int = 0
    pending_emails: int = 0
    failed_emails: int = 0
    queued_emails: int = 0
    # Reply statistics
    replies_received: int = 0
    positive_replies: int = 0
    interested_leads: int = 0
    meetings_requested: int = 0
    follow_ups_scheduled: int = 0
    follow_ups_completed: int = 0
    no_response_leads: int = 0
    # Campaign statistics
    completed_campaigns: int = 0
    running_campaigns: int = 0
    paused_campaigns: int = 0
    # AI statistics
    ai_emails_generated: int = 0
    ai_replies_generated: int = 0
    ai_tokens_used: int = 0
    estimated_ai_cost: float = 0.0
    # Gmail / agent
    gmail_connected: bool = False
    gmail_email: str | None = None
    daily_sending_limit: int = 50
    emails_remaining_today: int = 0
    sync_status: str = "unknown"
    last_sync_time: datetime | None = None
    agent_running: bool = False
    agent_paused: bool = False
    last_agent_run_at: datetime | None = None
    within_working_hours: bool = True
    # Rates
    success_rate: float = 0.0
    conversion_rate: float = 0.0
    # Widgets
    recent_activity: list[dict] = []
    recent_replies: list[dict] = []
    upcoming_followups: list[dict] = []
    running_jobs: int = 0


class AgentStatusResponse(BaseModel):
    agent_running: bool
    agent_paused: bool
    automation_enabled: bool
    gmail_connected: bool
    gmail_email: str | None
    daily_limit: int
    emails_sent_today: int
    emails_remaining_today: int
    last_sync_at: str | None
    last_agent_run_at: str | None
    standing_campaign_id: int | None
    within_working_hours: bool
    batch_delay_minutes: int = 10


class NotificationResponse(BaseModel):
    id: int
    notification_type: str
    title: str
    message: str
    lead_id: int | None
    is_read: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class ActivityLogResponse(BaseModel):
    id: int
    activity_type: str
    message: str
    lead_id: int | None
    level: str
    created_at: datetime

    model_config = {"from_attributes": True}


class PilotEmailResponse(BaseModel):
    lead_id: int
    company_name: str | None
    to_email: str
    subject: str
    body_text: str
    status: str


class ManualLeadOutreachResponse(BaseModel):
    message: str
    subject: str
    to_email: str
    status: str
    lead_id: int
    company_name: str | None = None


class AgentActionResponse(BaseModel):
    status: str
    message: str
    campaign_id: int | None = None
    batch_scheduled_at: str | None = None
    pilot_email: PilotEmailResponse | None = None


class OAuthStartResponse(BaseModel):
    authorization_url: str


class CampaignLaunchResponse(BaseModel):
    campaign_id: int
    status: str
    message: str
    jobs_enqueued: int
