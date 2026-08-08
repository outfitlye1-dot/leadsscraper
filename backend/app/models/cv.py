import enum
from datetime import UTC, datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class CVFileType(str, enum.Enum):
    pdf = "pdf"
    docx = "docx"


class CV(Base):
    __tablename__ = "cv_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    original_filename: Mapped[str] = mapped_column(String(500), nullable=False)
    file_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    file_type: Mapped[CVFileType] = mapped_column(Enum(CVFileType), nullable=False)
    raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    skills: Mapped[list | None] = mapped_column(JSON, nullable=True, default=list)
    experience: Mapped[list | None] = mapped_column(JSON, nullable=True, default=list)
    education: Mapped[list | None] = mapped_column(JSON, nullable=True, default=list)
    projects: Mapped[list | None] = mapped_column(JSON, nullable=True, default=list)
    services: Mapped[list | None] = mapped_column(JSON, nullable=True, default=list)
    tools: Mapped[list | None] = mapped_column(JSON, nullable=True, default=list)
    technologies: Mapped[list | None] = mapped_column(JSON, nullable=True, default=list)
    professional_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    skills_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    services_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    experience_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    user = relationship("User", back_populates="cv_profiles")
