from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.models.email_otp import EmailOtp, OtpPurpose


def _as_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


class EmailOtpRepository:
    def __init__(self, db: Session):
        self.db = db

    def delete_for_email(self, email: str, purpose: OtpPurpose) -> None:
        self.db.query(EmailOtp).filter(
            EmailOtp.email == email,
            EmailOtp.purpose == purpose,
        ).delete()
        self.db.commit()

    def create(self, email: str, code_hash: str, purpose: OtpPurpose, expires_at: datetime) -> EmailOtp:
        row = EmailOtp(
            email=email,
            code_hash=code_hash,
            purpose=purpose,
            expires_at=expires_at,
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def get_latest(self, email: str, purpose: OtpPurpose) -> EmailOtp | None:
        return (
            self.db.query(EmailOtp)
            .filter(EmailOtp.email == email, EmailOtp.purpose == purpose)
            .order_by(EmailOtp.created_at.desc())
            .first()
        )

    def record_attempt(self, row: EmailOtp) -> EmailOtp:
        row.attempts += 1
        self.db.commit()
        self.db.refresh(row)
        return row

    def delete(self, row: EmailOtp) -> None:
        self.db.delete(row)
        self.db.commit()

    def seconds_since_last_send(self, email: str, purpose: OtpPurpose) -> float | None:
        row = self.get_latest(email, purpose)
        if not row:
            return None
        return (datetime.now(UTC) - _as_utc(row.created_at)).total_seconds()
