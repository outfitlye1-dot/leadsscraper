import logging

from fastapi import HTTPException, status
from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType

from app.core.config import get_settings

logger = logging.getLogger(__name__)

_PURPOSE_COPY = {
    "login": {
        "subject": "Your sign-in code",
        "headline": "Sign in to your account",
        "hint": "Use this code to sign in. You can also use your password if you remember it.",
    },
    "register": {
        "subject": "Verify your email",
        "headline": "Complete your registration",
        "hint": "Enter this code to verify your email and activate your account.",
    },
    "reset_password": {
        "subject": "Reset your password",
        "headline": "Password reset request",
        "hint": "You requested a password reset. Enter this code and choose a new password.",
    },
}


def _mail_config() -> ConnectionConfig:
    settings = get_settings()
    mail_from = settings.SMTP_FROM or settings.SMTP_USER
    return ConnectionConfig(
        MAIL_USERNAME=settings.SMTP_USER,
        MAIL_PASSWORD=settings.SMTP_PASSWORD,
        MAIL_FROM=mail_from,
        MAIL_FROM_NAME=settings.SMTP_FROM_NAME,
        MAIL_PORT=settings.SMTP_PORT,
        MAIL_SERVER=settings.SMTP_HOST,
        MAIL_STARTTLS=True,
        MAIL_SSL_TLS=False,
        USE_CREDENTIALS=True,
        VALIDATE_CERTS=True,
    )


class EmailService:
    async def send_otp(self, email: str, code: str, *, purpose: str) -> None:
        settings = get_settings()
        brand = settings.SMTP_FROM_NAME or "LeadGen AI"
        copy = _PURPOSE_COPY.get(purpose, _PURPOSE_COPY["login"])
        subject = f"{copy['subject']} — {brand}"
        body = f"""{copy['headline']}

Your verification code:

    {code}

{copy['hint']}

This code expires in {settings.OTP_EXPIRE_MINUTES} minutes.
If you did not request this, you can safely ignore this email.

— {brand}
"""

        if not settings.smtp_configured:
            if settings.effective_otp_dev_mode:
                logger.warning("OTP_DEV_MODE: code for %s is %s", email, code)
                return
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=(
                    "Gmail SMTP not configured. Add SMTP_USER, SMTP_PASSWORD, and SMTP_FROM "
                    "to .env (use a Gmail App Password)."
                ),
            )

        message = MessageSchema(
            subject=subject,
            recipients=[email],
            body=body,
            subtype=MessageType.plain,
        )
        try:
            fm = FastMail(_mail_config())
            await fm.send_message(message)
        except Exception as exc:
            logger.exception("Failed to send OTP email to %s", email)
            err = str(exc)
            if "Application-specific password required" in err or "5.7.9" in err:
                detail = (
                    "Gmail App Password required. Do not use your normal Gmail password. "
                    "Enable 2-Step Verification, then create an App Password at "
                    "https://myaccount.google.com/apppasswords and put it in SMTP_PASSWORD."
                )
            elif "Username and Password not accepted" in err or "5.7.8" in err or "535" in err:
                detail = (
                    "Gmail rejected SMTP login. Check: (1) SMTP_PASSWORD is a 16-character "
                    "App Password (not your normal Gmail password), (2) SMTP_USER and SMTP_FROM "
                    "are the same Gmail address, (3) if the password contains # put it in quotes "
                    'in .env e.g. SMTP_PASSWORD="yourapppassword".'
                )
            else:
                detail = f"Failed to send OTP email: {exc}"
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=detail,
            ) from exc
