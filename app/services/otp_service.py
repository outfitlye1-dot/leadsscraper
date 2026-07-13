import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import create_access_token, get_password_hash
from app.models.email_otp import OtpPurpose
from app.repositories.email_otp_repository import EmailOtpRepository
from app.repositories.user_repository import UserRepository
from app.schemas.user import OtpSendRequest, OtpSendResponse, OtpVerifyRequest
from app.services.email_service import EmailService


def _as_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


class OtpService:
    def __init__(self, db: Session):
        self.db = db
        self.users = UserRepository(db)
        self.otps = EmailOtpRepository(db)
        self.mailer = EmailService()

    @staticmethod
    def _normalize_email(email: str) -> str:
        return email.strip().lower()

    @staticmethod
    def _generate_code() -> str:
        return f"{secrets.randbelow(1_000_000):06d}"

    def _hash_code(self, email: str, code: str) -> str:
        settings = get_settings()
        payload = f"{email}:{code}".encode()
        return hmac.new(settings.SECRET_KEY.encode(), payload, hashlib.sha256).hexdigest()

    def _verify_code_hash(self, email: str, code: str, code_hash: str) -> bool:
        return hmac.compare_digest(self._hash_code(email, code), code_hash)

    def _validate_send_request(self, email: str, purpose: OtpPurpose) -> None:
        user = self.users.get_by_email(email)

        if purpose in (OtpPurpose.login, OtpPurpose.reset_password) and not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Account nahi mili. Pehle register karein.",
            )
        if purpose == OtpPurpose.register and user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered. Login karein.",
            )

    def _issue_token(self, user_id: int) -> dict:
        settings = get_settings()
        access_token = create_access_token(
            data={"sub": str(user_id)},
            expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        )
        return {"access_token": access_token, "token_type": "bearer"}

    async def send_otp(self, data: OtpSendRequest) -> OtpSendResponse:
        settings = get_settings()
        email = self._normalize_email(str(data.email))
        purpose = OtpPurpose(data.purpose)

        self._validate_send_request(email, purpose)

        elapsed = self.otps.seconds_since_last_send(email, purpose)
        if elapsed is not None and elapsed < settings.OTP_RESEND_COOLDOWN_SECONDS:
            wait = int(settings.OTP_RESEND_COOLDOWN_SECONDS - elapsed)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Please wait {wait}s before requesting another code.",
            )

        code = self._generate_code()
        expires_at = datetime.now(UTC) + timedelta(minutes=settings.OTP_EXPIRE_MINUTES)

        await self.mailer.send_otp(email, code, purpose=purpose.value)

        self.otps.delete_for_email(email, purpose)
        self.otps.create(email, self._hash_code(email, code), purpose, expires_at)

        message = f"OTP sent to {email}"
        if settings.effective_otp_dev_mode and not settings.smtp_configured:
            message = f"Dev mode: OTP logged on server for {email}"

        return OtpSendResponse(
            message=message,
            expires_in_minutes=settings.OTP_EXPIRE_MINUTES,
        )

    def _consume_otp(self, email: str, purpose: OtpPurpose, code: str) -> None:
        settings = get_settings()

        if not code.isdigit() or len(code) != 6:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="OTP must be a 6-digit code.",
            )

        row = self.otps.get_latest(email, purpose)
        if not row:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No OTP found. Request a new code.",
            )

        if _as_utc(row.expires_at) < datetime.now(UTC):
            self.otps.delete(row)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="OTP expired. Request a new code.",
            )

        if row.attempts >= settings.OTP_MAX_VERIFY_ATTEMPTS:
            self.otps.delete(row)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Too many attempts. Request a new code.",
            )

        if not self._verify_code_hash(email, code, row.code_hash):
            self.otps.record_attempt(row)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid OTP code.",
            )

        self.otps.delete(row)

    def verify_otp(self, data: OtpVerifyRequest) -> dict:
        email = self._normalize_email(str(data.email))
        purpose = OtpPurpose(data.purpose)
        code = data.code.strip()

        self._consume_otp(email, purpose, code)

        if purpose == OtpPurpose.register:
            name = (data.name or "").strip()
            password = data.password or ""
            if len(name) < 2:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Name is required for registration.",
                )
            if len(password) < 8:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Password is required (min 8 characters).",
                )
            if self.users.get_by_email(email):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Email already registered.",
                )
            user = self.users.create(
                name=name,
                email=email,
                password_hash=get_password_hash(password),
            )
            return self._issue_token(user.id)

        if purpose == OtpPurpose.reset_password:
            password = data.password or ""
            if len(password) < 8:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="New password is required (min 8 characters).",
                )
            user = self.users.get_by_email(email)
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Account not found.",
                )
            self.users.update_password(user, get_password_hash(password))
            return self._issue_token(user.id)

        user = self.users.get_by_email(email)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Account not found.",
            )
        return self._issue_token(user.id)
