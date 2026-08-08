"""Manual WhatsApp reply assistant — one isolated thread + memory per lead/phone."""

from datetime import UTC, datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class WhatsAppChatThread(Base):
    """One chat vault per saved lead/phone — AI must only use this thread's memory."""

    __tablename__ = "whatsapp_chat_threads"
    __table_args__ = (
        UniqueConstraint("user_id", "lead_id", name="uq_wa_thread_user_lead"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    lead_id: Mapped[int] = mapped_column(
        ForeignKey("leads.id", ondelete="CASCADE"), index=True, nullable=False
    )
    phone: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    # Rolling memory so AI remembers deals/facts for THIS number only
    memory_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_price_quoted: Mapped[float | None] = mapped_column(Float, nullable=True)
    customer_budget: Mapped[float | None] = mapped_column(Float, nullable=True)
    deal_status: Mapped[str | None] = mapped_column(String(40), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    user = relationship("User")
    lead = relationship("Lead")
    messages = relationship(
        "WhatsAppChatMessage",
        back_populates="thread",
        cascade="all, delete-orphan",
        order_by="WhatsAppChatMessage.id",
    )


class WhatsAppChatMessage(Base):
    __tablename__ = "whatsapp_chat_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    lead_id: Mapped[int] = mapped_column(
        ForeignKey("leads.id", ondelete="CASCADE"), index=True, nullable=False
    )
    thread_id: Mapped[int | None] = mapped_column(
        ForeignKey("whatsapp_chat_threads.id", ondelete="CASCADE"),
        index=True,
        nullable=True,
    )
    phone: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    # inbound = customer WhatsApp text you pasted
    # outbound = draft for you to copy-send manually
    direction: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
        index=True,
    )

    user = relationship("User")
    lead = relationship("Lead")
    thread = relationship("WhatsAppChatThread", back_populates="messages")
