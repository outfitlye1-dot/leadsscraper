from sqlalchemy.orm import Session

from app.models.campaign import MessageType
from app.models.message import Message


class MessageRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, user_id: int, data: dict) -> Message:
        message = Message(user_id=user_id, **data)
        self.db.add(message)
        self.db.commit()
        self.db.refresh(message)
        return message

    def get_by_id(self, user_id: int, message_id: int) -> Message | None:
        return (
            self.db.query(Message)
            .filter(Message.id == message_id, Message.user_id == user_id)
            .first()
        )

    def search(
        self,
        user_id: int,
        lead_id: int | None = None,
        campaign_id: int | None = None,
        message_type: MessageType | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Message], int]:
        query = self.db.query(Message).filter(Message.user_id == user_id)

        if lead_id:
            query = query.filter(Message.lead_id == lead_id)
        if campaign_id:
            query = query.filter(Message.campaign_id == campaign_id)
        if message_type:
            query = query.filter(Message.message_type == message_type)

        total = query.count()
        messages = (
            query.order_by(Message.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return messages, total

    def count_by_user(self, user_id: int) -> int:
        return self.db.query(Message).filter(Message.user_id == user_id).count()

    def count_by_campaign(self, user_id: int, campaign_id: int) -> int:
        return (
            self.db.query(Message)
            .filter(Message.user_id == user_id, Message.campaign_id == campaign_id)
            .count()
        )

    def exists_for_lead_campaign(self, user_id: int, lead_id: int, campaign_id: int) -> bool:
        return (
            self.db.query(Message.id)
            .filter(
                Message.user_id == user_id,
                Message.lead_id == lead_id,
                Message.campaign_id == campaign_id,
            )
            .first()
            is not None
        )

    def _filtered_query(
        self,
        user_id: int,
        lead_id: int | None = None,
        campaign_id: int | None = None,
        message_type: MessageType | None = None,
    ):
        query = self.db.query(Message).filter(Message.user_id == user_id)
        if lead_id:
            query = query.filter(Message.lead_id == lead_id)
        if campaign_id:
            query = query.filter(Message.campaign_id == campaign_id)
        if message_type:
            query = query.filter(Message.message_type == message_type)
        return query

    def delete_matching(
        self,
        user_id: int,
        lead_id: int | None = None,
        campaign_id: int | None = None,
        message_type: MessageType | None = None,
    ) -> int:
        count = self._filtered_query(
            user_id, lead_id=lead_id, campaign_id=campaign_id, message_type=message_type
        ).delete(synchronize_session=False)
        self.db.commit()
        return count
