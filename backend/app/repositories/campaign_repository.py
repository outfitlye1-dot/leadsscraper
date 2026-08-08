from sqlalchemy.orm import Session

from app.models.campaign import Campaign


class CampaignRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, user_id: int, data: dict) -> Campaign:
        campaign = Campaign(user_id=user_id, **data)
        self.db.add(campaign)
        self.db.commit()
        self.db.refresh(campaign)
        return campaign

    def get_by_id(self, user_id: int, campaign_id: int) -> Campaign | None:
        return (
            self.db.query(Campaign)
            .filter(Campaign.id == campaign_id, Campaign.user_id == user_id)
            .first()
        )

    def get_all(self, user_id: int) -> list[Campaign]:
        return (
            self.db.query(Campaign)
            .filter(Campaign.user_id == user_id)
            .order_by(Campaign.created_at.desc())
            .all()
        )

    def update(self, campaign: Campaign, data: dict) -> Campaign:
        for key, value in data.items():
            if value is not None:
                setattr(campaign, key, value)
        self.db.commit()
        self.db.refresh(campaign)
        return campaign

    def delete(self, campaign: Campaign) -> None:
        self.db.delete(campaign)
        self.db.commit()

    def count_by_user(self, user_id: int) -> int:
        return self.db.query(Campaign).filter(Campaign.user_id == user_id).count()
