"""Persistent JSON settings for WhatsApp Web automation (not Cloud API)."""

from __future__ import annotations

import json
import logging
import threading
from pathlib import Path
from typing import Any

from app.core.config import get_settings

logger = logging.getLogger(__name__)

_DEFAULTS: dict[str, Any] = {
    "auto_reply": True,
    "ignore_phones": [],
    "ignore_groups": True,
    "human_takeover_phones": [],
    # Bound from frontend login when user clicks Connect / Start
    "owner_user_id": None,
    "owner_email": "",
    # Daily outbound AI openers to saved leads (WhatsApp Web)
    "daily_outreach_enabled": False,
    "daily_outreach_limit": 5,
    "daily_outreach_sent_date": "",
    "daily_outreach_sent_count": 0,
    # Minutes between outreach attempts (success or fail) — default 1 hour
    "daily_outreach_interval_minutes": 60,
    "daily_outreach_last_attempt_at": "",
}


class WhatsAppWebSettingsStore:
    """File-backed settings under the Playwright profile directory."""

    def __init__(self, path: Path | None = None) -> None:
        settings = get_settings()
        profile = Path(settings.WA_WEB_PROFILE_DIR)
        if not profile.is_absolute():
            from app.core.config import BASE_DIR

            profile = BASE_DIR / profile
        self._path = path or (profile / "wa_web_settings.json")
        self._lock = threading.Lock()
        self._path.parent.mkdir(parents=True, exist_ok=True)

    @property
    def path(self) -> Path:
        return self._path

    def _read(self) -> dict[str, Any]:
        if not self._path.exists():
            return dict(_DEFAULTS)
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                return dict(_DEFAULTS)
            merged = dict(_DEFAULTS)
            merged.update(data)
            return merged
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("Failed to read WA Web settings (%s); using defaults", exc)
            return dict(_DEFAULTS)

    def _write(self, data: dict[str, Any]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(self._path)

    def get_all(self) -> dict[str, Any]:
        with self._lock:
            return self._read()

    def update(self, **kwargs: Any) -> dict[str, Any]:
        with self._lock:
            data = self._read()
            for key, value in kwargs.items():
                if key not in _DEFAULTS:
                    continue
                if key == "daily_outreach_limit":
                    try:
                        value = max(1, min(10, int(value)))
                    except (TypeError, ValueError):
                        value = 5
                if key == "daily_outreach_sent_count":
                    try:
                        value = max(0, int(value))
                    except (TypeError, ValueError):
                        value = 0
                if key == "daily_outreach_enabled":
                    value = bool(value)
                if key == "daily_outreach_interval_minutes":
                    try:
                        value = max(1, min(24 * 60, int(value)))
                    except (TypeError, ValueError):
                        value = 60
                data[key] = value
            self._write(data)
            return dict(data)

    def daily_outreach_quota(self) -> dict[str, Any]:
        """Return today's remaining daily outreach quota (UTC day)."""
        from datetime import UTC, datetime, timedelta

        data = self.get_all()
        today = datetime.now(UTC).strftime("%Y-%m-%d")
        sent_date = str(data.get("daily_outreach_sent_date") or "")
        try:
            limit = max(1, min(10, int(data.get("daily_outreach_limit") or 5)))
        except (TypeError, ValueError):
            limit = 5
        try:
            sent = int(data.get("daily_outreach_sent_count") or 0)
        except (TypeError, ValueError):
            sent = 0
        if sent_date != today:
            sent = 0
            sent_date = today
        remaining = max(0, limit - sent)
        try:
            interval_minutes = max(
                1, min(24 * 60, int(data.get("daily_outreach_interval_minutes") or 60))
            )
        except (TypeError, ValueError):
            interval_minutes = 60
        last_raw = str(data.get("daily_outreach_last_attempt_at") or "").strip()
        seconds_until_next = 0
        if last_raw:
            try:
                last_at = datetime.fromisoformat(last_raw.replace("Z", "+00:00"))
                if last_at.tzinfo is None:
                    last_at = last_at.replace(tzinfo=UTC)
                elapsed = datetime.now(UTC) - last_at.astimezone(UTC)
                wait = timedelta(minutes=interval_minutes) - elapsed
                seconds_until_next = max(0, int(wait.total_seconds()))
            except ValueError:
                seconds_until_next = 0
        return {
            "enabled": bool(data.get("daily_outreach_enabled", False)),
            "limit": limit,
            "sent_date": sent_date,
            "sent_count": sent,
            "remaining": remaining,
            "interval_minutes": interval_minutes,
            "seconds_until_next": seconds_until_next,
            "ready": seconds_until_next <= 0,
        }

    def record_daily_outreach_attempt(self) -> None:
        """Mark an outreach attempt (success or fail) for the interval cooldown."""
        from datetime import UTC, datetime

        with self._lock:
            data = self._read()
            data["daily_outreach_last_attempt_at"] = datetime.now(UTC).isoformat()
            self._write(data)

    def record_daily_outreach_send(self) -> dict[str, Any]:
        """Increment today's sent count after a successful outbound opener."""
        from datetime import UTC, datetime

        with self._lock:
            data = self._read()
            today = datetime.now(UTC).strftime("%Y-%m-%d")
            if str(data.get("daily_outreach_sent_date") or "") != today:
                data["daily_outreach_sent_date"] = today
                data["daily_outreach_sent_count"] = 0
            try:
                data["daily_outreach_sent_count"] = int(data.get("daily_outreach_sent_count") or 0) + 1
            except (TypeError, ValueError):
                data["daily_outreach_sent_count"] = 1
            try:
                data["daily_outreach_limit"] = max(
                    1, min(10, int(data.get("daily_outreach_limit") or 5))
                )
            except (TypeError, ValueError):
                data["daily_outreach_limit"] = 5
            data["daily_outreach_last_attempt_at"] = datetime.now(UTC).isoformat()
            self._write(data)
            sent = int(data["daily_outreach_sent_count"])
            limit = int(data["daily_outreach_limit"])
            try:
                interval_minutes = max(
                    1, min(24 * 60, int(data.get("daily_outreach_interval_minutes") or 60))
                )
            except (TypeError, ValueError):
                interval_minutes = 60
            return {
                "enabled": bool(data.get("daily_outreach_enabled", False)),
                "limit": limit,
                "sent_date": today,
                "sent_count": sent,
                "remaining": max(0, limit - sent),
                "interval_minutes": interval_minutes,
                "seconds_until_next": interval_minutes * 60,
                "ready": False,
            }

    def set_owner(self, user_id: int, email: str = "") -> dict[str, Any]:
        """Bind AI auto-reply to the logged-in app user (Saved leads + Brain)."""
        return self.update(
            owner_user_id=int(user_id),
            owner_email=(email or "").strip().lower(),
        )

    def get_owner_user_id(self) -> int | None:
        raw = self.get_all().get("owner_user_id")
        try:
            uid = int(raw) if raw is not None else 0
        except (TypeError, ValueError):
            return None
        return uid if uid > 0 else None

    def is_auto_reply_enabled(self) -> bool:
        return bool(self.get_all().get("auto_reply", True))

    def is_phone_ignored(self, phone: str) -> bool:
        digits = "".join(c for c in (phone or "") if c.isdigit())
        if not digits:
            return False
        ignored = self.get_all().get("ignore_phones") or []
        for item in ignored:
            item_digits = "".join(c for c in str(item) if c.isdigit())
            if item_digits and (digits.endswith(item_digits) or item_digits.endswith(digits)):
                return True
        return False

    def is_human_takeover(self, phone: str) -> bool:
        digits = "".join(c for c in (phone or "") if c.isdigit())
        if not digits:
            return False
        takeover = self.get_all().get("human_takeover_phones") or []
        for item in takeover:
            item_digits = "".join(c for c in str(item) if c.isdigit())
            if item_digits and (digits.endswith(item_digits) or item_digits.endswith(digits)):
                return True
        return False
