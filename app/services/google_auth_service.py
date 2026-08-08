"""Google OAuth sign-in / sign-up for app authentication."""

from __future__ import annotations

import secrets
from datetime import timedelta
from urllib.parse import quote, urlencode

import httpx
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import create_access_token, get_password_hash
from app.repositories.user_repository import UserRepository

_auth_oauth_states: dict[str, dict[str, str]] = {}

GOOGLE_AUTH_SCOPES = ["openid", "email", "profile"]
GOOGLE_AUTH_CALLBACK_PATH = "/api/auth/google/callback"


def _callback_origin(redirect_uri: str) -> str:
    from urllib.parse import urlparse

    parsed = urlparse(redirect_uri)
    return f"{parsed.scheme}://{parsed.netloc}"


class GoogleAuthService:
    def __init__(self, db: Session):
        self.db = db
        self.users = UserRepository(db)

    def _allowed_redirect_uris(self) -> set[str]:
        settings = get_settings()
        frontend = settings.FRONTEND_URL.rstrip("/")
        candidates = {
            settings.GOOGLE_AUTH_REDIRECT_URI.rstrip("/"),
            f"{frontend}{GOOGLE_AUTH_CALLBACK_PATH}",
            "http://localhost:3000/api/auth/google/callback",
            "http://127.0.0.1:3000/api/auth/google/callback",
        }
        return {uri for uri in candidates if uri}

    def _resolve_redirect_uri(self, requested: str | None) -> str:
        allowed = self._allowed_redirect_uris()
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Google sign-in redirect URI is not configured.",
            )
        if not requested:
            return next(iter(sorted(allowed)))

        normalized = requested.strip().rstrip("/")
        if normalized not in allowed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Invalid Google redirect URI. Add this exact URI in Google Cloud Console: "
                    f"{normalized}"
                ),
            )
        return normalized

    def start(self, redirect_uri: str | None = None) -> str:
        settings = get_settings()
        if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Google sign-in not configured. Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET.",
            )
        resolved_redirect_uri = self._resolve_redirect_uri(redirect_uri)
        state = secrets.token_urlsafe(32)
        _auth_oauth_states[state] = {
            "redirect_uri": resolved_redirect_uri,
            "frontend_origin": _callback_origin(resolved_redirect_uri),
        }
        params = {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "redirect_uri": resolved_redirect_uri,
            "response_type": "code",
            "scope": " ".join(GOOGLE_AUTH_SCOPES),
            "access_type": "online",
            "prompt": "select_account",
            "state": state,
        }
        return f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"

    def handle_callback(self, code: str, state: str) -> str:
        settings = get_settings()
        ctx = _auth_oauth_states.pop(state, None)
        if not ctx:
            return self._frontend_error(
                "Invalid or expired Google sign-in session. Try again.",
                settings.FRONTEND_URL,
            )

        redirect_uri = ctx["redirect_uri"]
        frontend_origin = ctx["frontend_origin"]

        try:
            profile = self._exchange_code_for_profile(code, redirect_uri)
        except HTTPException as exc:
            return self._frontend_error(str(exc.detail), frontend_origin)

        google_id = profile.get("id") or profile.get("sub")
        email = (profile.get("email") or "").strip().lower()
        name = (profile.get("name") or email.split("@")[0] or "User").strip()
        avatar_url = (profile.get("picture") or "").strip() or None

        if not google_id or not email:
            return self._frontend_error(
                "Google did not return email or profile id.",
                frontend_origin,
            )

        if not profile.get("verified_email", True):
            return self._frontend_error("Google email is not verified.", frontend_origin)

        user = self.users.get_by_google_id(google_id)
        if not user:
            existing = self.users.get_by_email(email)
            if existing:
                if existing.google_id and existing.google_id != google_id:
                    return self._frontend_error(
                        "This email is linked to a different Google account.",
                        frontend_origin,
                    )
                existing.google_id = google_id
                if name and existing.name != name:
                    existing.name = name
                if avatar_url:
                    existing.avatar_url = avatar_url
                self.db.commit()
                self.db.refresh(existing)
                user = existing
            else:
                password_hash = get_password_hash(secrets.token_urlsafe(48))
                user = self.users.create(
                    name=name,
                    email=email,
                    password_hash=password_hash,
                    google_id=google_id,
                    avatar_url=avatar_url,
                )

        access_token = create_access_token(
            data={"sub": str(user.id)},
            expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        )
        return f"{frontend_origin}/login?access_token={access_token}"

    def _exchange_code_for_profile(self, code: str, redirect_uri: str) -> dict:
        settings = get_settings()
        with httpx.Client(timeout=20.0) as client:
            token_resp = client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "code": code,
                    "client_id": settings.GOOGLE_CLIENT_ID,
                    "client_secret": settings.GOOGLE_CLIENT_SECRET,
                    "redirect_uri": redirect_uri,
                    "grant_type": "authorization_code",
                },
            )
            if token_resp.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        "Google sign-in failed. Add this redirect URI in Google Cloud Console: "
                        f"{redirect_uri}"
                    ),
                )
            tokens = token_resp.json()
            access_token = tokens.get("access_token")
            if not access_token:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Google did not return an access token.",
                )

            profile_resp = client.get(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            profile_resp.raise_for_status()
            return profile_resp.json()

    @staticmethod
    def _frontend_error(message: str, frontend_origin: str | None = None) -> str:
        settings = get_settings()
        base = (frontend_origin or settings.FRONTEND_URL).rstrip("/")
        return f"{base}/login?error={quote(message)}"
