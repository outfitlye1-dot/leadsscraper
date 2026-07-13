from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class Brain(Base):
    __tablename__ = "brains"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False, unique=True
    )
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    skills: Mapped[list | None] = mapped_column(JSON, nullable=True, default=list)
    experience: Mapped[list | None] = mapped_column(JSON, nullable=True, default=list)
    education: Mapped[list | None] = mapped_column(JSON, nullable=True, default=list)
    projects: Mapped[list | None] = mapped_column(JSON, nullable=True, default=list)
    services: Mapped[list | None] = mapped_column(JSON, nullable=True, default=list)
    tools: Mapped[list | None] = mapped_column(JSON, nullable=True, default=list)
    technologies: Mapped[list | None] = mapped_column(JSON, nullable=True, default=list)
    professional_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    custom_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    system_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    user = relationship("User", back_populates="brain")
