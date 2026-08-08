import enum
from datetime import UTC, date, datetime

from sqlalchemy import Boolean, Date, DateTime, Enum, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class UserRole(str, enum.Enum):
    user = "user"
    admin = "admin"


class UserPlan(str, enum.Enum):
    free = "free"
    paid = "paid"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    google_id: Mapped[str | None] = mapped_column(String(255), unique=True, index=True, nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.user, nullable=False)
    api_access: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    plan: Mapped[UserPlan] = mapped_column(Enum(UserPlan), default=UserPlan.free, nullable=False)
    daily_token_limit: Mapped[int] = mapped_column(Integer, default=50, nullable=False)
    tokens_used_today: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    tokens_reset_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    own_api_keys_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    own_api_keys_requested: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    paid_plan_requested: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    leads = relationship("Lead", back_populates="user", cascade="all, delete-orphan")
    cv_profiles = relationship("CV", back_populates="user", cascade="all, delete-orphan")
    brain = relationship("Brain", back_populates="user", cascade="all, delete-orphan", uselist=False)
    campaigns = relationship("Campaign", back_populates="user", cascade="all, delete-orphan")
    messages = relationship("Message", back_populates="user", cascade="all, delete-orphan")
    api_keys = relationship("UserApiKey", back_populates="user", cascade="all, delete-orphan")
    daily_scrape_runs = relationship(
        "DailyScrapeRun", back_populates="user", cascade="all, delete-orphan"
    )
    email_accounts = relationship(
        "EmailAccount", back_populates="user", cascade="all, delete-orphan"
    )
    email_outreach_settings = relationship(
        "EmailOutreachSettings", back_populates="user", cascade="all, delete-orphan", uselist=False
    )
    email_outreach_campaigns = relationship(
        "EmailOutreachCampaign", back_populates="user", cascade="all, delete-orphan"
    )
    outreach_emails = relationship(
        "OutreachEmail", back_populates="user", cascade="all, delete-orphan"
    )
    email_conversations = relationship(
        "EmailConversation", back_populates="user", cascade="all, delete-orphan"
    )
    email_timeline_events = relationship(
        "EmailTimelineEvent", back_populates="user", cascade="all, delete-orphan"
    )
    outreach_jobs = relationship(
        "OutreachJob", back_populates="user", cascade="all, delete-orphan"
    )
    ai_reply_drafts = relationship(
        "AiReplyDraft", back_populates="user", cascade="all, delete-orphan"
    )
    outreach_notifications = relationship(
        "OutreachNotification", back_populates="user", cascade="all, delete-orphan"
    )
    agent_activity_logs = relationship(
        "AgentActivityLog", back_populates="user", cascade="all, delete-orphan"
    )
