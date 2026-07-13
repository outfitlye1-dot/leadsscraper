"""OAuth flows for Gmail and Microsoft Outlook."""

from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta
from urllib.parse import urlencode

import httpx
from fastapi import HTTPException, status

from app.core.config import get_settings
from app.models.email_outreach import EmailAccountStatus, EmailProvider
from app.repositories.email_outreach_repository import EmailOutreachRepository
from app.utils.secret_encryption import encrypt_secret

_oauth_states: dict[str, dict] = {}


class OAuthService:
    GOOGLE_SCOPES = [
        "https://mail.google.com/",
        "openid",
        "email",
        "profile",
    ]
    MICROSOFT_SCOPES = [
        "https://outlook.office.com/IMAP.AccessAsUser.All",
        "https://outlook.office.com/SMTP.Send",
        "offline_access",
        "openid",
        "email",
        "profile",
    ]

    def __init__(self, repo: EmailOutreachRepository):
        self.repo = repo

    def start_google(self, user_id: int) -> str:
        settings = get_settings()
        if not settings.GOOGLE_CLIENT_ID:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Google OAuth not configured. Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET.",
            )
        state = secrets.token_urlsafe(32)
        _oauth_states[state] = {"user_id": user_id, "provider": "gmail_oauth"}
        params = {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "redirect_uri": settings.GOOGLE_OAUTH_REDIRECT_URI,
            "response_type": "code",
            "scope": " ".join(self.GOOGLE_SCOPES),
            "access_type": "offline",
            "prompt": "consent",
            "state": state,
        }
        return f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"

    def start_microsoft(self, user_id: int) -> str:
        settings = get_settings()
        if not settings.MICROSOFT_CLIENT_ID:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Microsoft OAuth not configured. Set MICROSOFT_CLIENT_ID and MICROSOFT_CLIENT_SECRET.",
            )
        state = secrets.token_urlsafe(32)
        _oauth_states[state] = {"user_id": user_id, "provider": "outlook_oauth"}
        params = {
            "client_id": settings.MICROSOFT_CLIENT_ID,
            "redirect_uri": settings.MICROSOFT_OAUTH_REDIRECT_URI,
            "response_type": "code",
            "scope": " ".join(self.MICROSOFT_SCOPES),
            "state": state,
        }
        return (
            "https://login.microsoftonline.com/common/oauth2/v2.0/authorize?"
            f"{urlencode(params)}"
        )

    def handle_google_callback(self, code: str, state: str) -> str:
        ctx = _oauth_states.pop(state, None)
        if not ctx:
            raise HTTPException(status_code=400, detail="Invalid OAuth state")
        settings = get_settings()
        with httpx.Client(timeout=20.0) as client:
            resp = client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "code": code,
                    "client_id": settings.GOOGLE_CLIENT_ID,
                    "client_secret": settings.GOOGLE_CLIENT_SECRET,
                    "redirect_uri": settings.GOOGLE_OAUTH_REDIRECT_URI,
                    "grant_type": "authorization_code",
                },
            )
            resp.raise_for_status()
            tokens = resp.json()

        email_address = self._fetch_google_email(tokens["access_token"])
        self._save_oauth_account(
            ctx["user_id"],
            EmailProvider.gmail_oauth,
            email_address,
            tokens,
        )
        return f"{settings.FRONTEND_URL}/email-outreach?connected=gmail"

    def handle_microsoft_callback(self, code: str, state: str) -> str:
        ctx = _oauth_states.pop(state, None)
        if not ctx:
            raise HTTPException(status_code=400, detail="Invalid OAuth state")
        settings = get_settings()
        with httpx.Client(timeout=20.0) as client:
            resp = client.post(
                "https://login.microsoftonline.com/common/oauth2/v2.0/token",
                data={
                    "code": code,
                    "client_id": settings.MICROSOFT_CLIENT_ID,
                    "client_secret": settings.MICROSOFT_CLIENT_SECRET,
                    "redirect_uri": settings.MICROSOFT_OAUTH_REDIRECT_URI,
                    "grant_type": "authorization_code",
                    "scope": " ".join(self.MICROSOFT_SCOPES),
                },
            )
            resp.raise_for_status()
            tokens = resp.json()

        email_address = self._fetch_microsoft_email(tokens["access_token"])
        self._save_oauth_account(
            ctx["user_id"],
            EmailProvider.outlook_oauth,
            email_address,
            tokens,
        )
        return f"{settings.FRONTEND_URL}/email-outreach?connected=outlook"

    def _fetch_google_email(self, access_token: str) -> str:
        with httpx.Client(timeout=15.0) as client:
            resp = client.get(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            resp.raise_for_status()
            return resp.json().get("email", "")

    def _fetch_microsoft_email(self, access_token: str) -> str:
        with httpx.Client(timeout=15.0) as client:
            resp = client.get(
                "https://graph.microsoft.com/v1.0/me",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            resp.raise_for_status()
            return resp.json().get("mail") or resp.json().get("userPrincipalName", "")

    def _save_oauth_account(
        self, user_id: int, provider: EmailProvider, email_address: str, tokens: dict
    ) -> None:
        expires_in = int(tokens.get("expires_in", 3600))
        existing = next(
            (a for a in self.repo.list_accounts(user_id) if a.email_address == email_address),
            None,
        )
        data = {
            "provider": provider,
            "email_address": email_address,
            "oauth_access_token_encrypted": encrypt_secret(tokens.get("access_token", "")),
            "oauth_refresh_token_encrypted": encrypt_secret(tokens.get("refresh_token", "")),
            "oauth_expires_at": datetime.now(UTC) + timedelta(seconds=expires_in),
            "smtp_host": "smtp.gmail.com" if provider == EmailProvider.gmail_oauth else "smtp.office365.com",
            "smtp_port": 587,
            "imap_host": "imap.gmail.com" if provider == EmailProvider.gmail_oauth else "outlook.office365.com",
            "imap_port": 993,
            "status": EmailAccountStatus.connected,
            "last_error": None,
        }
        if existing:
            self.repo.update_account(existing, data)
        else:
            accounts = self.repo.list_accounts(user_id)
            data["is_default"] = len(accounts) == 0
            self.repo.create_account(user_id, data)
