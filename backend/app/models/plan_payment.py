import enum
from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class PaymentStatus(str, enum.Enum):
    pending = "pending"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"


class PlanPayment(Base):
    __tablename__ = "plan_payments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    txn_ref_no: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    amount_paisa: Mapped[int] = mapped_column(Integer, nullable=False)
    plan: Mapped[str] = mapped_column(String(32), default="pro", nullable=False)
    provider: Mapped[str] = mapped_column(String(32), default="jazzcash", nullable=False)
    status: Mapped[PaymentStatus] = mapped_column(
        String(32), default=PaymentStatus.pending.value, nullable=False
    )
    response_code: Mapped[str | None] = mapped_column(String(16), nullable=True)
    response_message: Mapped[str | None] = mapped_column(String(512), nullable=True)
    raw_response: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    user = relationship("User", backref="plan_payments")
