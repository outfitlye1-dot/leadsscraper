"""DB models for WhatsApp Web inbound queue (separate from Cloud API tables)."""

from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class WhatsAppWebInboundJob(Base):
    """Queued inbound WhatsApp Web message awaiting AI auto-reply."""

    __tablename__ = "whatsapp_web_inbound_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    dedupe_key: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    chat_title: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    phone_hint: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    # pending | processing | done | failed | skipped
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending", index=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    lead_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    user_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    reply_body: Mapped[str | None] = mapped_column(Text, nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    ai_replied: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
        index=True,
    )
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
