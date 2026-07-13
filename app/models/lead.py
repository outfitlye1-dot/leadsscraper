import enum
from datetime import UTC, datetime

from sqlalchemy import JSON, Boolean, DateTime, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class LeadStatus(str, enum.Enum):
    new = "new"
    contacted = "contacted"
    interested = "interested"
    follow_up = "follow_up"
    closed = "closed"
    lost = "lost"


class IntentTier(str, enum.Enum):
    hot = "hot"
    warm = "warm"
    cold = "cold"


class Lead(Base):
    __tablename__ = "leads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    company_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    contact_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    website: Mapped[str | None] = mapped_column(String(500), nullable=True, index=True)
    linkedin_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    facebook_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    instagram_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    postal_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    category: Mapped[str | None] = mapped_column(String(255), nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    country: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    industry: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    source: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[LeadStatus] = mapped_column(
        Enum(LeadStatus), default=LeadStatus.new, nullable=False, index=True
    )
    quality_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    quality_tier: Mapped[str | None] = mapped_column(String(20), nullable=True)
    whatsapp_ready: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    phone_verified: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    email_verified: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    website_quality_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    website_opportunity_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    website_problems: Mapped[list | None] = mapped_column(JSON, nullable=True)
    reviews_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rating: Mapped[float | None] = mapped_column(Float, nullable=True)
    business_hours: Mapped[str | None] = mapped_column(Text, nullable=True)
    google_profile_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    photos_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    buying_intent_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    intent_tier: Mapped[str | None] = mapped_column(String(10), nullable=True, index=True)
    social_activity_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    social_links_verified: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    is_running_ads: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    ads_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ad_platform: Mapped[str | None] = mapped_column(String(50), nullable=True)
    landing_page: Mapped[str | None] = mapped_column(String(500), nullable=True)
    ad_activity_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ai_qualification: Mapped[str | None] = mapped_column(String(20), nullable=True)
    recommended_offer: Mapped[str | None] = mapped_column(Text, nullable=True)
    qualification_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    niche_key: Mapped[str | None] = mapped_column(String(50), nullable=True)
    recommended_service: Mapped[str | None] = mapped_column(String(255), nullable=True)
    intelligence_meta: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    is_saved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    saved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False, index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    user = relationship("User", back_populates="leads")
    messages = relationship("Message", back_populates="lead")
    outreach_emails = relationship("OutreachEmail", back_populates="lead")
    email_conversations = relationship("EmailConversation", back_populates="lead")
    email_timeline_events = relationship("EmailTimelineEvent", back_populates="lead")
