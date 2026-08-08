"""Meta WhatsApp Cloud API client (official Graph API)."""

from __future__ import annotations

import logging
import re
from typing import Any

import httpx
from fastapi import HTTPException, status

from app.core.config import get_settings

logger = logging.getLogger(__name__)


def normalize_wa_to(phone: str) -> str:
    """WhatsApp Cloud API expects digits only with country code (no +)."""
    digits = re.sub(r"\D", "", (phone or "").strip())
    if digits.startswith("00"):
        digits = digits[2:]
    if len(digits) < 10 or len(digits) > 15:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid recipient phone — need country code + number",
        )
    return digits


class WhatsAppCloudService:
    def __init__(self) -> None:
        self.settings = get_settings()

    def status(self) -> dict[str, Any]:
        return {
            "configured": self.settings.whatsapp_cloud_configured,
            "phone_number_id": self.settings.WHATSAPP_PHONE_NUMBER_ID or None,
            "business_account_id": self.settings.WHATSAPP_BUSINESS_ACCOUNT_ID or None,
            "display_number": self.settings.WHATSAPP_TEST_DISPLAY_NUMBER or None,
            "api_version": self.settings.WHATSAPP_API_VERSION,
        }

    def _require_configured(self) -> None:
        if not self.settings.whatsapp_cloud_configured:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=(
                    "WhatsApp Cloud API not configured. "
                    "Set WHATSAPP_ACCESS_TOKEN and WHATSAPP_PHONE_NUMBER_ID in .env"
                ),
            )

    def _url(self, path: str) -> str:
        version = (self.settings.WHATSAPP_API_VERSION or "v21.0").strip()
        if not version.startswith("v"):
            version = f"v{version}"
        return f"https://graph.facebook.com/{version}/{path.lstrip('/')}"

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.settings.WHATSAPP_ACCESS_TOKEN.strip()}",
            "Content-Type": "application/json",
        }

    def send_text(self, *, to_phone: str, body: str) -> dict[str, Any]:
        """Send a free-form text message (allowed inside the 24h customer-care window)."""
        self._require_configured()
        text = (body or "").strip()
        if not text:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Message body required")
        to = normalize_wa_to(to_phone)
        phone_id = self.settings.WHATSAPP_PHONE_NUMBER_ID.strip()
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "text",
            "text": {"preview_url": False, "body": text[:4096]},
        }
        return self._post(f"{phone_id}/messages", payload)

    def send_template(
        self,
        *,
        to_phone: str,
        template_name: str = "hello_world",
        language_code: str = "en_US",
    ) -> dict[str, Any]:
        """Send an approved template (needed to start chats outside the 24h window)."""
        self._require_configured()
        to = normalize_wa_to(to_phone)
        phone_id = self.settings.WHATSAPP_PHONE_NUMBER_ID.strip()
        name = (template_name or "hello_world").strip()
        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "template",
            "template": {
                "name": name,
                "language": {"code": language_code or "en_US"},
            },
        }
        return self._post(f"{phone_id}/messages", payload)

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        url = self._url(path)
        try:
            with httpx.Client(timeout=30.0) as client:
                resp = client.post(url, headers=self._headers(), json=payload)
        except httpx.HTTPError as exc:
            logger.warning("WhatsApp Cloud API network error: %s", exc)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"WhatsApp API network error: {exc}",
            ) from exc

        data: dict[str, Any]
        try:
            data = resp.json()
        except Exception:
            data = {"raw": resp.text}

        if resp.status_code >= 400:
            err = data.get("error") if isinstance(data, dict) else None
            message = None
            if isinstance(err, dict):
                message = err.get("message") or err.get("error_user_msg")
            detail = message or f"WhatsApp API error ({resp.status_code})"
            # Common Meta restriction: free text only after customer messages you
            if "24" in str(detail).lower() or "template" in str(detail).lower():
                detail = (
                    f"{detail} — Tip: first outbound to a new number usually needs an "
                    "approved template (or the customer must message you first)."
                )
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=detail)

        message_id = None
        try:
            message_id = data["messages"][0]["id"]
        except Exception:
            pass
        return {
            "success": True,
            "message_id": message_id,
            "to": payload.get("to"),
            "raw": data,
        }
