"""Email outreach automation models."""

from __future__ import annotations

import enum
from datetime import UTC, datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class EmailProvider(str, enum.Enum):
    gmail_oauth = "gmail_oauth"
    outlook_oauth = "outlook_oauth"
    smtp = "smtp"
    imap = "imap"


class EmailAccountStatus(str, enum.Enum):
    connected = "connected"
    disconnected = "disconnected"
    error = "error"


class OutreachCampaignStatus(str, enum.Enum):
    draft = "draft"
    verifying = "verifying"
    generating = "generating"
    review = "review"
    sending = "sending"
    active = "active"
    paused = "paused"
    completed = "completed"


class OutreachEmailStatus(str, enum.Enum):
    pending_verification = "pending_verification"
    verification_failed = "verification_failed"
    draft = "draft"
    pending_review = "pending_review"
    approved = "approved"
    queued = "queued"
    sending = "sending"
    sent = "sent"
    delivered = "delivered"
    opened = "opened"
    replied = "replied"
    bounced = "bounced"
    failed = "failed"
    cancelled = "cancelled"


class ConversationStatus(str, enum.Enum):
    active = "active"
    responded = "responded"
    closed = "closed"


class ReplyIntent(str, enum.Enum):
    interested = "interested"
    not_interested = "not_interested"
    question = "question"
    meeting_request = "meeting_request"
    unsubscribe = "unsubscribe"
    out_of_office = "out_of_office"
    other = "other"


class OutreachJobType(str, enum.Enum):
    verify_emails = "verify_emails"
    generate_emails = "generate_emails"
    send_email = "send_email"
    sync_inbox = "sync_inbox"
    detect_replies = "detect_replies"
    schedule_followups = "schedule_followups"
    process_campaign = "process_campaign"
    generate_ai_reply = "generate_ai_reply"
    agent_cycle = "agent_cycle"
    process_lead = "process_lead"


class OutreachJobStatus(str, enum.Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"


class AiReplyDraftStatus(str, enum.Enum):
    pending_approval = "pending_approval"
    approved = "approved"
    sent = "sent"
    rejected = "rejected"
    auto_sent = "auto_sent"


class EmailTimelineEventType(str, enum.Enum):
    email_sent = "email_sent"
    delivered = "delivered"
    opened = "opened"
    replied = "replied"
    bounced = "bounced"
    follow_up_scheduled = "follow_up_scheduled"
    follow_up_sent = "follow_up_sent"
    status_changed = "status_changed"
    ai_draft_created = "ai_draft_created"
    unsubscribed = "unsubscribed"
    email_verified = "email_verified"
    ai_email_generated = "ai_email_generated"
    lead_created = "lead_created"
    meeting_requested = "meeting_requested"
    agent_started = "agent_started"
    agent_stopped = "agent_stopped"


class NotificationType(str, enum.Enum):
    email_sent = "email_sent"
    reply_received = "reply_received"
    follow_up_sent = "follow_up_sent"
    campaign_completed = "campaign_completed"
    gmail_disconnected = "gmail_disconnected"
    daily_limit_reached = "daily_limit_reached"
    agent_stopped = "agent_stopped"
    agent_started = "agent_started"
    error = "error"
    lead_processed = "lead_processed"


class EmailAccount(Base):
    __tablename__ = "email_accounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    provider: Mapped[EmailProvider] = mapped_column(Enum(EmailProvider), nullable=False)
    email_address: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    encrypted_credentials: Mapped[str | None] = mapped_column(Text, nullable=True)
    oauth_access_token_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    oauth_refresh_token_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    oauth_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    smtp_host: Mapped[str | None] = mapped_column(String(255), nullable=True)
    smtp_port: Mapped[int | None] = mapped_column(Integer, nullable=True)
    imap_host: Mapped[str | None] = mapped_column(String(255), nullable=True)
    imap_port: Mapped[int | None] = mapped_column(Integer, nullable=True)
    use_tls: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    status: Mapped[EmailAccountStatus] = mapped_column(
        Enum(EmailAccountStatus), default=EmailAccountStatus.disconnected, nullable=False
    )
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    daily_sent_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    daily_sent_reset_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    user = relationship("User", back_populates="email_accounts")


class EmailOutreachSettings(Base):
    __tablename__ = "email_outreach_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True, nullable=False
    )
    automation_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    auto_send_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    require_review: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    daily_send_limit: Mapped[int] = mapped_column(Integer, default=20, nullable=False)
    hourly_send_limit: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    rate_limit_per_minute: Mapped[int] = mapped_column(Integer, default=2, nullable=False)
    auto_reply_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    auto_reply_simple_only: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    include_unsubscribe: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    default_email_account_id: Mapped[int | None] = mapped_column(
        ForeignKey("email_accounts.id", ondelete="SET NULL"), nullable=True
    )
    # AI Agent settings
    agent_running: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    agent_paused: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    auto_follow_up: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    working_hours_start: Mapped[int] = mapped_column(Integer, default=9, nullable=False)
    working_hours_end: Mapped[int] = mapped_column(Integer, default=18, nullable=False)
    weekends_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    standing_campaign_id: Mapped[int | None] = mapped_column(
        ForeignKey("email_outreach_campaigns.id", ondelete="SET NULL"), nullable=True
    )
    last_agent_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ai_emails_generated: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    ai_replies_generated: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    agent_batch_delay_minutes: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    user = relationship("User", back_populates="email_outreach_settings")


class EmailOutreachCampaign(Base):
    __tablename__ = "email_outreach_campaigns"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    campaign_id: Mapped[int | None] = mapped_column(
        ForeignKey("campaigns.id", ondelete="SET NULL"), index=True, nullable=True
    )
    email_account_id: Mapped[int | None] = mapped_column(
        ForeignKey("email_accounts.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[OutreachCampaignStatus] = mapped_column(
        Enum(OutreachCampaignStatus), default=OutreachCampaignStatus.draft, nullable=False, index=True
    )
    automation_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    require_review: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    follow_up_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    lead_filter_saved_only: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    lead_ids: Mapped[list | None] = mapped_column(JSON, nullable=True)
    stats: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    user = relationship("User", back_populates="email_outreach_campaigns")
    follow_up_steps = relationship(
        "FollowUpStep", back_populates="outreach_campaign", cascade="all, delete-orphan"
    )
    outreach_emails = relationship(
        "OutreachEmail", back_populates="outreach_campaign", cascade="all, delete-orphan"
    )


class FollowUpStep(Base):
    __tablename__ = "follow_up_steps"
    __table_args__ = (
        UniqueConstraint("outreach_campaign_id", "step_number", name="uq_follow_up_step"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    outreach_campaign_id: Mapped[int] = mapped_column(
        ForeignKey("email_outreach_campaigns.id", ondelete="CASCADE"), index=True, nullable=False
    )
    step_number: Mapped[int] = mapped_column(Integer, nullable=False)
    delay_days: Mapped[int] = mapped_column(Integer, nullable=False)
    subject_override: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    outreach_campaign = relationship("EmailOutreachCampaign", back_populates="follow_up_steps")


class OutreachEmail(Base):
    __tablename__ = "outreach_emails"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    outreach_campaign_id: Mapped[int] = mapped_column(
        ForeignKey("email_outreach_campaigns.id", ondelete="CASCADE"), index=True, nullable=False
    )
    lead_id: Mapped[int] = mapped_column(
        ForeignKey("leads.id", ondelete="CASCADE"), index=True, nullable=False
    )
    email_account_id: Mapped[int | None] = mapped_column(
        ForeignKey("email_accounts.id", ondelete="SET NULL"), nullable=True
    )
    follow_up_step: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    to_email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    subject: Mapped[str] = mapped_column(String(500), nullable=False)
    body_text: Mapped[str] = mapped_column(Text, nullable=False)
    body_html: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[OutreachEmailStatus] = mapped_column(
        Enum(OutreachEmailStatus), default=OutreachEmailStatus.pending_verification, nullable=False, index=True
    )
    verification_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    verification_details: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    external_message_id: Mapped[str | None] = mapped_column(String(500), nullable=True, index=True)
    thread_id: Mapped[str | None] = mapped_column(String(500), nullable=True, index=True)
    in_reply_to: Mapped[str | None] = mapped_column(String(500), nullable=True)
    tracking_token: Mapped[str | None] = mapped_column(String(64), nullable=True, unique=True, index=True)
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    opened_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    replied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_generated: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_follow_up: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    user = relationship("User", back_populates="outreach_emails")
    outreach_campaign = relationship("EmailOutreachCampaign", back_populates="outreach_emails")
    lead = relationship("Lead", back_populates="outreach_emails")


class EmailConversation(Base):
    __tablename__ = "email_conversations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    lead_id: Mapped[int] = mapped_column(
        ForeignKey("leads.id", ondelete="CASCADE"), index=True, nullable=False
    )
    outreach_campaign_id: Mapped[int | None] = mapped_column(
        ForeignKey("email_outreach_campaigns.id", ondelete="SET NULL"), nullable=True
    )
    email_account_id: Mapped[int | None] = mapped_column(
        ForeignKey("email_accounts.id", ondelete="SET NULL"), nullable=True
    )
    subject: Mapped[str] = mapped_column(String(500), nullable=False)
    thread_id: Mapped[str | None] = mapped_column(String(500), nullable=True, index=True)
    status: Mapped[ConversationStatus] = mapped_column(
        Enum(ConversationStatus), default=ConversationStatus.active, nullable=False
    )
    reply_intent: Mapped[ReplyIntent | None] = mapped_column(Enum(ReplyIntent), nullable=True)
    reply_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    follow_ups_stopped: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    last_message_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    user = relationship("User", back_populates="email_conversations")
    lead = relationship("Lead", back_populates="email_conversations")
    messages = relationship(
        "ConversationMessage", back_populates="conversation", cascade="all, delete-orphan"
    )


class ConversationMessage(Base):
    __tablename__ = "conversation_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    conversation_id: Mapped[int] = mapped_column(
        ForeignKey("email_conversations.id", ondelete="CASCADE"), index=True, nullable=False
    )
    outreach_email_id: Mapped[int | None] = mapped_column(
        ForeignKey("outreach_emails.id", ondelete="SET NULL"), nullable=True
    )
    direction: Mapped[str] = mapped_column(String(10), nullable=False)  # outbound | inbound
    from_email: Mapped[str] = mapped_column(String(255), nullable=False)
    to_email: Mapped[str] = mapped_column(String(255), nullable=False)
    subject: Mapped[str] = mapped_column(String(500), nullable=False)
    body_text: Mapped[str] = mapped_column(Text, nullable=False)
    body_html: Mapped[str | None] = mapped_column(Text, nullable=True)
    external_message_id: Mapped[str | None] = mapped_column(String(500), nullable=True, index=True)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )

    conversation = relationship("EmailConversation", back_populates="messages")


class EmailTimelineEvent(Base):
    __tablename__ = "email_timeline_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    lead_id: Mapped[int] = mapped_column(
        ForeignKey("leads.id", ondelete="CASCADE"), index=True, nullable=False
    )
    outreach_email_id: Mapped[int | None] = mapped_column(
        ForeignKey("outreach_emails.id", ondelete="SET NULL"), nullable=True
    )
    conversation_id: Mapped[int | None] = mapped_column(
        ForeignKey("email_conversations.id", ondelete="SET NULL"), nullable=True
    )
    event_type: Mapped[EmailTimelineEventType] = mapped_column(
        Enum(EmailTimelineEventType), nullable=False, index=True
    )
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    event_meta: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False, index=True
    )

    user = relationship("User", back_populates="email_timeline_events")
    lead = relationship("Lead", back_populates="email_timeline_events")


class OutreachJob(Base):
    __tablename__ = "outreach_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    job_type: Mapped[OutreachJobType] = mapped_column(Enum(OutreachJobType), nullable=False, index=True)
    payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    status: Mapped[OutreachJobStatus] = mapped_column(
        Enum(OutreachJobStatus), default=OutreachJobStatus.pending, nullable=False, index=True
    )
    priority: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    idempotency_key: Mapped[str | None] = mapped_column(String(128), nullable=True, unique=True, index=True)
    scheduled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False, index=True
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )

    user = relationship("User", back_populates="outreach_jobs")


class AiReplyDraft(Base):
    __tablename__ = "ai_reply_drafts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    conversation_id: Mapped[int] = mapped_column(
        ForeignKey("email_conversations.id", ondelete="CASCADE"), index=True, nullable=False
    )
    inbound_message_id: Mapped[int | None] = mapped_column(
        ForeignKey("conversation_messages.id", ondelete="SET NULL"), nullable=True
    )
    detected_intent: Mapped[ReplyIntent] = mapped_column(Enum(ReplyIntent), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    draft_subject: Mapped[str] = mapped_column(String(500), nullable=False)
    draft_body: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[AiReplyDraftStatus] = mapped_column(
        Enum(AiReplyDraftStatus), default=AiReplyDraftStatus.pending_approval, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    user = relationship("User", back_populates="ai_reply_drafts")
    conversation = relationship("EmailConversation")


class OutreachNotification(Base):
    __tablename__ = "outreach_notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    notification_type: Mapped[NotificationType] = mapped_column(
        Enum(NotificationType), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    lead_id: Mapped[int | None] = mapped_column(
        ForeignKey("leads.id", ondelete="SET NULL"), nullable=True
    )
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False, index=True
    )

    user = relationship("User", back_populates="outreach_notifications")


class AgentActivityLog(Base):
    __tablename__ = "agent_activity_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    activity_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    message: Mapped[str] = mapped_column(String(500), nullable=False)
    lead_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    level: Mapped[str] = mapped_column(String(20), default="info", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False, index=True
    )

    user = relationship("User", back_populates="agent_activity_logs")
