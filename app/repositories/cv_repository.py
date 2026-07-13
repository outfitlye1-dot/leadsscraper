from sqlalchemy.orm import Session

from app.models.cv import CV


class CVRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_latest_by_user(self, user_id: int) -> CV | None:
        return (
            self.db.query(CV)
            .filter(CV.user_id == user_id)
            .order_by(CV.created_at.desc())
            .first()
        )

    def create_or_update(self, user_id: int, data: dict) -> CV:
        existing = self.get_latest_by_user(user_id)
        if existing:
            for key, value in data.items():
                setattr(existing, key, value)
            self.db.commit()
            self.db.refresh(existing)
            return existing

        cv = CV(user_id=user_id, **data)
        self.db.add(cv)
        self.db.commit()
        self.db.refresh(cv)
        return cv
