"""Top-level email outreach service — accounts, settings, dashboard."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.email_outreach import (
    EmailAccountStatus,
    EmailProvider,
)
from app.models.user import User
from app.repositories.email_outreach_repository import EmailOutreachRepository
from app.schemas.email_outreach import (
    EmailAccountResponse,
    EmailOutreachDashboardResponse,
    EmailOutreachSettingsResponse,
    EmailOutreachSettingsUpdateRequest,
    EmailVerificationResponse,
    SmtpAccountCreateRequest,
    TimelineEventResponse,
)
from app.services.email_outreach.dashboard import OutreachDashboardService
from app.services.email_outreach.oauth import OAuthService
from app.services.email_outreach.verification import verify_outreach_email
from app.utils.secret_encryption import encrypt_json


class EmailOutreachService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = EmailOutreachRepository(db)
        self.oauth = OAuthService(self.repo)

    def list_accounts(self, user: User) -> list[EmailAccountResponse]:
        return [EmailAccountResponse.model_validate(a) for a in self.repo.list_accounts(user.id)]

    def connect_smtp(self, user: User, data: SmtpAccountCreateRequest) -> EmailAccountResponse:
        accounts = self.repo.list_accounts(user.id)
        if data.is_default or not accounts:
            for a in accounts:
                if a.is_default:
                    self.repo.update_account(a, {"is_default": False})

        account = self.repo.create_account(
            user.id,
            {
                "provider": EmailProvider.smtp,
                "email_address": data.email_address.strip().lower(),
                "display_name": data.display_name or data.email_address,
                "encrypted_credentials": encrypt_json({"password": data.password}),
                "smtp_host": data.smtp_host,
                "smtp_port": data.smtp_port,
                "imap_host": data.imap_host,
                "imap_port": data.imap_port,
                "use_tls": data.use_tls,
                "status": EmailAccountStatus.connected,
                "is_default": data.is_default or not accounts,
            },
        )
        settings = self.repo.get_or_create_settings(user.id)
        if not settings.default_email_account_id:
            settings.default_email_account_id = account.id
            self.db.commit()
        return EmailAccountResponse.model_validate(account)

    def delete_account(self, user: User, account_id: int) -> None:
        account = self.repo.get_account(user.id, account_id)
        if not account:
            raise HTTPException(status_code=404, detail="Account not found")
        self.repo.delete_account(account)

    def set_default_account(self, user: User, account_id: int) -> EmailAccountResponse:
        account = self.repo.get_account(user.id, account_id)
        if not account:
            raise HTTPException(status_code=404, detail="Account not found")
        for a in self.repo.list_accounts(user.id):
            if a.is_default:
                self.repo.update_account(a, {"is_default": False})
        updated = self.repo.update_account(account, {"is_default": True})
        settings = self.repo.get_or_create_settings(user.id)
        settings.default_email_account_id = account.id
        self.db.commit()
        return EmailAccountResponse.model_validate(updated)

    def get_settings(self, user: User) -> EmailOutreachSettingsResponse:
        return EmailOutreachSettingsResponse.model_validate(
            self.repo.get_or_create_settings(user.id)
        )

    def update_settings(
        self, user: User, data: EmailOutreachSettingsUpdateRequest
    ) -> EmailOutreachSettingsResponse:
        settings = self.repo.get_or_create_settings(user.id)
        for key, value in data.model_dump(exclude_unset=True).items():
            setattr(settings, key, value)
        settings.updated_at = datetime.now(UTC)
        self.db.commit()
        self.db.refresh(settings)
        return EmailOutreachSettingsResponse.model_validate(settings)

    def verify_email(self, email: str, website: str | None = None) -> EmailVerificationResponse:
        result = verify_outreach_email(email, website)
        return EmailVerificationResponse(**result.to_dict())

    def get_dashboard(self, user: User) -> EmailOutreachDashboardResponse:
        stats = OutreachDashboardService(self.db).build_stats(user.id)
        return EmailOutreachDashboardResponse(**stats)

    def get_lead_timeline(self, user: User, lead_id: int) -> list[TimelineEventResponse]:
        events = self.repo.list_timeline(user.id, lead_id)
        return [TimelineEventResponse.model_validate(e) for e in events]

    def start_google_oauth(self, user: User) -> str:
        return self.oauth.start_google(user.id)

    def start_microsoft_oauth(self, user: User) -> str:
        return self.oauth.start_microsoft(user.id)
