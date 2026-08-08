from sqlalchemy.orm import Session

from app.models.brain import Brain


class BrainRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_user(self, user_id: int) -> Brain | None:
        return self.db.query(Brain).filter(Brain.user_id == user_id).first()

    def upsert(self, user_id: int, data: dict) -> Brain:
        existing = self.get_by_user(user_id)
        if existing:
            for key, value in data.items():
                if value is not None:
                    setattr(existing, key, value)
            self.db.commit()
            self.db.refresh(existing)
            return existing

        brain = Brain(user_id=user_id, **{k: v for k, v in data.items() if v is not None})
        self.db.add(brain)
        self.db.commit()
        self.db.refresh(brain)
        return brain
