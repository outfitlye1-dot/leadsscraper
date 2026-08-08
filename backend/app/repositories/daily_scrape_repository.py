from datetime import date

from sqlalchemy.orm import Session

from app.models.daily_scrape_run import DailyScrapeRun


class DailyScrapeRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_for_user_date(self, user_id: int, run_date: date) -> DailyScrapeRun | None:
        return (
            self.db.query(DailyScrapeRun)
            .filter(DailyScrapeRun.user_id == user_id, DailyScrapeRun.run_date == run_date)
            .first()
        )

    def get_latest_for_user(self, user_id: int) -> DailyScrapeRun | None:
        return (
            self.db.query(DailyScrapeRun)
            .filter(DailyScrapeRun.user_id == user_id)
            .order_by(DailyScrapeRun.run_date.desc())
            .first()
        )

    def create(
        self,
        user_id: int,
        run_date: date,
        job_id: str,
        *,
        leads_target: int,
        search_query: str,
    ) -> DailyScrapeRun:
        record = DailyScrapeRun(
            user_id=user_id,
            run_date=run_date,
            job_id=job_id,
            leads_target=leads_target,
            search_query=search_query,
        )
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record
