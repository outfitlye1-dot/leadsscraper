"""User notifications for outreach events."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.email_outreach import NotificationType, OutreachNotification


class NotificationService:
    def __init__(self, db: Session):
        self.db = db

    def notify(
        self,
        user_id: int,
        notification_type: NotificationType,
        title: str,
        message: str,
        *,
        lead_id: int | None = None,
    ) -> OutreachNotification:
        row = OutreachNotification(
            user_id=user_id,
            notification_type=notification_type,
            title=title,
            message=message,
            lead_id=lead_id,
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def list_unread(self, user_id: int, limit: int = 50) -> list[OutreachNotification]:
        return (
            self.db.query(OutreachNotification)
            .filter(
                OutreachNotification.user_id == user_id,
                OutreachNotification.is_read.is_(False),
            )
            .order_by(OutreachNotification.created_at.desc())
            .limit(limit)
            .all()
        )

    def list_recent(self, user_id: int, limit: int = 50) -> list[OutreachNotification]:
        return (
            self.db.query(OutreachNotification)
            .filter(OutreachNotification.user_id == user_id)
            .order_by(OutreachNotification.created_at.desc())
            .limit(limit)
            .all()
        )

    def mark_read(self, user_id: int, notification_id: int) -> None:
        row = (
            self.db.query(OutreachNotification)
            .filter(
                OutreachNotification.user_id == user_id,
                OutreachNotification.id == notification_id,
            )
            .first()
        )
        if row:
            row.is_read = True
            self.db.commit()

    def mark_read_for_lead(self, user_id: int, lead_id: int) -> int:
        rows = (
            self.db.query(OutreachNotification)
            .filter(
                OutreachNotification.user_id == user_id,
                OutreachNotification.lead_id == lead_id,
                OutreachNotification.is_read.is_(False),
            )
            .all()
        )
        for row in rows:
            row.is_read = True
        if rows:
            self.db.commit()
        return len(rows)

    def mark_all_read(self, user_id: int) -> int:
        rows = (
            self.db.query(OutreachNotification)
            .filter(
                OutreachNotification.user_id == user_id,
                OutreachNotification.is_read.is_(False),
            )
            .all()
        )
        for row in rows:
            row.is_read = True
        if rows:
            self.db.commit()
        return len(rows)
