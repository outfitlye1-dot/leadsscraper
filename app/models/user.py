import enum
from datetime import UTC, datetime

from sqlalchemy import DateTime, Enum, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class UserRole(str, enum.Enum):
    user = "user"
    admin = "admin"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.user, nullable=False)
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
