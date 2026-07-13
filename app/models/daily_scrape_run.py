from datetime import UTC, date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class DailyScrapeRun(Base):
    __tablename__ = "daily_scrape_runs"
    __table_args__ = (UniqueConstraint("user_id", "run_date", name="uq_daily_scrape_user_date"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    run_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    job_id: Mapped[str] = mapped_column(String(64), nullable=False)
    leads_target: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    search_query: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )

    user = relationship("User", back_populates="daily_scrape_runs")
