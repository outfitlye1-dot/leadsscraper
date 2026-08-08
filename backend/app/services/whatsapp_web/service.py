"""Public facade for WhatsApp Web automation + AI auto-reply worker control."""

from __future__ import annotations

import logging
import time
from typing import Any

from fastapi import HTTPException, status

from app.core.config import get_settings
from app.database.database import SessionLocal
from app.models.user import User
from app.services.whatsapp_web import session as wa_session
from app.services.whatsapp_web.browser import wa_web_browser
from app.services.whatsapp_web.queue import WhatsAppWebQueue
from app.services.whatsapp_web.settings_store import WhatsAppWebSettingsStore
from app.services.whatsapp_web.worker import wa_web_worker

logger = logging.getLogger(__name__)


class WhatsAppWebService:
    def __init__(self) -> None:
        self.settings_store = WhatsAppWebSettingsStore()

    def _require_enabled(self) -> None:
        if not get_settings().WA_WEB_ENABLED:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="WhatsApp Web automation is disabled. Set WA_WEB_ENABLED=true in .env",
            )

    def bind_owner(self, user: User) -> dict[str, Any]:
        """Use the currently logged-in app user for Saved leads + Brain AI replies."""
        return self.settings_store.set_owner(int(user.id), getattr(user, "email", "") or "")

    def status(self) -> dict[str, Any]:
        settings = get_settings()
        store = self.settings_store.get_all()
        owner_id = store.get("owner_user_id")
        try:
            owner_id_int = int(owner_id) if owner_id is not None else None
        except (TypeError, ValueError):
            owner_id_int = None
        payload: dict[str, Any] = {
            "enabled": bool(settings.WA_WEB_ENABLED),
            "headless": bool(settings.WA_WEB_HEADLESS),
            "profile_dir": (
                str(wa_web_browser.profile_dir())
                if settings.WA_WEB_ENABLED
                else settings.WA_WEB_PROFILE_DIR
            ),
            "browser_started": wa_web_browser.is_started(),
            "logged_in": False,
            "worker_running": wa_web_worker.is_running(),
            "auto_reply": bool(store.get("auto_reply", True)),
            "ignore_groups": bool(store.get("ignore_groups", True)),
            "owner_user_id": owner_id_int if owner_id_int and owner_id_int > 0 else None,
            "owner_email": (store.get("owner_email") or "") or None,
            "cdp_mode": wa_web_browser.is_cdp_mode(),
            "cdp_configured": bool((settings.WA_WEB_CDP_URL or "").strip()),
            "cdp_alive": False,
            "cloud_api_untouched": True,
            "message": None,
        }
        quota = self.settings_store.daily_outreach_quota()
        payload["daily_outreach_enabled"] = bool(quota.get("enabled"))
        payload["daily_outreach_limit"] = int(quota.get("limit") or 5)
        payload["daily_outreach_sent_count"] = int(quota.get("sent_count") or 0)
        payload["daily_outreach_remaining"] = int(quota.get("remaining") or 0)
        payload["daily_outreach_interval_minutes"] = int(quota.get("interval_minutes") or 60)
        payload["daily_outreach_seconds_until_next"] = int(quota.get("seconds_until_next") or 0)
        if not settings.WA_WEB_ENABLED:
            payload["message"] = "Disabled — Cloud API WhatsApp still works independently"
            return payload
        cdp_configured = bool((settings.WA_WEB_CDP_URL or "").strip())
        if cdp_configured:
            try:
                payload["cdp_alive"] = wa_web_browser.is_cdp_alive(timeout_seconds=0.8)
            except Exception:
                payload["cdp_alive"] = False
        if cdp_configured and not wa_web_browser.is_started():
            if payload.get("cdp_alive"):
                payload["message"] = (
                    "Chrome mein WhatsApp linked hai — app attach toot gaya (server reload). "
                    "Connect / Start AI dabao (ya 20s wait — auto-reattach)"
                )
            else:
                payload["message"] = (
                    "Business link: pehle Open Chrome for link, Chrome mein WhatsApp link karo, "
                    "phir Connect dabao"
                )
        try:
            if wa_web_browser.is_started():
                try:
                    payload["logged_in"] = wa_session.is_logged_in()
                    payload["cdp_mode"] = wa_web_browser.is_cdp_mode()
                    if payload["logged_in"]:
                        payload["message"] = "Linked — AI auto-reply ready"
                    elif payload.get("cdp_alive"):
                        payload["message"] = (
                            "Attached to Chrome magar chats detect nahi — Connect dubara dabao"
                        )
                except Exception as exc:
                    logger.warning("WA Web login check failed: %s", exc)
                    payload["message"] = (
                        "Browser busy or recovering — click Connect / Refresh QR again"
                    )
            elif not payload.get("message"):
                payload["message"] = "Browser not started — call /qr or /start to launch + scan QR"
        except Exception as exc:
            logger.exception("WA Web status check failed")
            payload["message"] = f"Status check error: {exc}"
        return payload

    def get_qr(self, user: User | None = None) -> dict[str, Any]:
        self._require_enabled()
        if user is not None:
            self.bind_owner(user)
        try:
            info = wa_session.ensure_session(navigate=True)
            if info.get("logged_in"):
                # Session ready — ensure AI worker is running
                wa_web_worker.start()
                return {
                    "logged_in": True,
                    "qr_data_url": None,
                    "message": "Already logged in — AI auto-reply worker active",
                }
            png = wa_session.capture_qr_png_bytes(wait_seconds=25.0)
            if not png:
                if wa_session.is_logged_in():
                    wa_web_worker.start()
                    return {
                        "logged_in": True,
                        "qr_data_url": None,
                        "message": "Logged in — AI auto-reply worker active",
                    }
                return {
                    "logged_in": False,
                    "qr_data_url": None,
                    "message": (
                        "QR not ready yet — wait for WhatsApp to load in the browser window, "
                        "then click Refresh QR. Keep WA_WEB_HEADLESS=false."
                    ),
                }
            return {
                "logged_in": False,
                "qr_data_url": wa_session.qr_png_to_data_url(png),
                "message": "Scan QR with WhatsApp → Linked devices. AI will auto-reply after login.",
            }
        except RuntimeError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=str(exc),
            ) from exc
        except Exception as exc:
            logger.exception("WA Web QR capture failed")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Failed to capture WhatsApp QR: {exc}",
            ) from exc

    def reconnect(self, user: User | None = None) -> dict[str, Any]:
        self._require_enabled()
        if user is not None:
            self.bind_owner(user)
        try:
            info = wa_session.reconnect()
            if info.get("logged_in"):
                wa_web_worker.start()
            return {
                "ok": True,
                "logged_in": bool(info.get("logged_in")),
                "profile_dir": info.get("profile_dir"),
                "message": "Browser relaunched with persistent profile",
            }
        except RuntimeError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=str(exc),
            ) from exc
        except Exception as exc:
            logger.exception("WA Web reconnect failed")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Reconnect failed: {exc}",
            ) from exc

    def start_automation(self, user: User | None = None) -> dict[str, Any]:
        """Attach to Chrome/CDP (QR if needed) + start AI auto-reply worker."""
        self._require_enabled()
        owner_email = None
        if user is not None:
            bound = self.bind_owner(user)
            owner_email = bound.get("owner_email") or getattr(user, "email", None)
        try:
            info = wa_session.ensure_session(navigate=True)
            logged_in = bool(info.get("logged_in"))
            # Stale Playwright CDP handles often miss the live chat DOM even when
            # Chrome already shows WhatsApp Business linked — soft reattach once.
            if not logged_in and (settings := get_settings()) and (settings.WA_WEB_CDP_URL or "").strip():
                try:
                    logger.info("WA Web Connect: CDP reattach (login not detected yet)")
                    wa_web_browser.reattach_cdp()
                    info = wa_session.ensure_session(navigate=True, settle_seconds=1.5)
                    logged_in = bool(info.get("logged_in"))
                except Exception as reattach_exc:
                    logger.warning("WA Web CDP reattach failed: %s", reattach_exc)
            if not logged_in:
                time.sleep(1.5)
                try:
                    logged_in = wa_session.is_logged_in()
                except Exception:
                    logged_in = False
            wa_web_worker.start()
            qr_url = None
            if logged_in:
                message = "Connected — WhatsApp linked, AI auto-reply on"
            else:
                png = wa_session.capture_qr_png_bytes(wait_seconds=8.0)
                if png:
                    qr_url = wa_session.qr_png_to_data_url(png)
                    message = "Scan QR to connect — then AI will auto-reply to new messages"
                else:
                    message = (
                        "Chrome attach ho gaya magar chats detect nahi hui. "
                        "WhatsApp Business wali Chrome window open rakho (chats dikhni chahiye), "
                        "phir Connect / Start AI dubara dabao"
                    )
            if owner_email:
                message = f"{message} (owner: {owner_email})"
            return {
                "ok": True,
                "logged_in": logged_in,
                "worker_running": wa_web_worker.is_running(),
                "qr_data_url": qr_url,
                "message": message,
                "owner_email": owner_email,
            }
        except RuntimeError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=str(exc),
            ) from exc
        except Exception as exc:
            logger.exception("WA Web start failed")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"WhatsApp Web start failed: {exc}",
            ) from exc

    def stop_automation(self) -> dict[str, Any]:
        self._require_enabled()
        wa_web_worker.stop()
        return {
            "ok": True,
            "worker_running": wa_web_worker.is_running(),
            "message": "AI auto-reply worker stop signaled",
        }

    def list_jobs(self, limit: int = 20) -> list[dict[str, Any]]:
        self._require_enabled()
        db = SessionLocal()
        try:
            jobs = WhatsAppWebQueue(db).recent(limit=limit)
            return [
                {
                    "id": j.id,
                    "chat_title": j.chat_title,
                    "phone_hint": j.phone_hint,
                    "body": j.body[:200],
                    "status": j.status,
                    "ai_replied": j.ai_replied,
                    "reply_body": (j.reply_body or "")[:200] or None,
                    "error_message": j.error_message,
                    "lead_id": j.lead_id,
                    "created_at": j.created_at.isoformat() if j.created_at else None,
                }
                for j in jobs
            ]
        finally:
            db.close()

    def get_settings(self) -> dict[str, Any]:
        self._require_enabled()
        return self.settings_store.get_all()

    def update_settings(self, **kwargs: Any) -> dict[str, Any]:
        self._require_enabled()
        return self.settings_store.update(**kwargs)

    def reset_session(self, user: User | None = None) -> dict[str, Any]:
        """Clear broken profile (common after Business 'Couldn't link') and reopen login."""
        self._require_enabled()
        if user is not None:
            self.bind_owner(user)
        try:
            info = wa_session.reset_session()
            wa_web_worker.start()
            qr_url = None
            message = "Session reset — scan a fresh QR (prefer Chrome window)"
            if not info.get("logged_in"):
                png = wa_session.capture_qr_png_bytes(wait_seconds=25.0)
                if png:
                    qr_url = wa_session.qr_png_to_data_url(png)
                    message = (
                        "Fresh QR ready. WhatsApp Business → Linked devices → Link a device. "
                        "If phone says Couldn't link: unlink old devices, turn off VPN, or use pair code."
                    )
            return {
                "ok": True,
                "logged_in": bool(info.get("logged_in")),
                "worker_running": wa_web_worker.is_running(),
                "qr_data_url": qr_url,
                "message": message,
            }
        except Exception as exc:
            logger.exception("WA Web reset failed")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Reset failed: {exc}",
            ) from exc

    def request_pair_code(self, phone: str, user: User | None = None) -> dict[str, Any]:
        self._require_enabled()
        if user is not None:
            self.bind_owner(user)
        try:
            data = wa_session.request_pair_code(phone)
            if data.get("logged_in"):
                wa_web_worker.start()
            return {
                "ok": True,
                "logged_in": bool(data.get("logged_in")),
                "pair_code": data.get("pair_code"),
                "phone": data.get("phone"),
                "message": data.get("message"),
            }
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        except RuntimeError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=str(exc),
            ) from exc
        except Exception as exc:
            logger.exception("WA Web pair code failed")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Pair code failed: {exc}",
            ) from exc

    def read_pair_code(self, user: User | None = None) -> dict[str, Any]:
        """Read code already shown in Chrome after user did manual steps."""
        self._require_enabled()
        if user is not None:
            self.bind_owner(user)
        try:
            data = wa_session.read_pair_code()
            if data.get("logged_in"):
                wa_web_worker.start()
            return {
                "ok": True,
                "logged_in": bool(data.get("logged_in")),
                "pair_code": data.get("pair_code"),
                "phone": None,
                "message": data.get("message"),
            }
        except RuntimeError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=str(exc),
            ) from exc
        except Exception as exc:
            logger.exception("WA Web read pair code failed")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Read pair code failed: {exc}",
            ) from exc

    def launch_chrome(self) -> dict[str, Any]:
        """Open real Chrome with remote debugging for Business linking."""
        self._require_enabled()
        try:
            data = wa_web_browser.launch_cdp_chrome_public()
            # If WhatsApp is already linked in that Chrome, attach + start AI now.
            if data.get("ok"):
                try:
                    info = wa_session.ensure_session(navigate=True)
                    if info.get("logged_in"):
                        wa_web_worker.start()
                        data["logged_in"] = True
                        data["worker_running"] = wa_web_worker.is_running()
                        data["attached"] = True
                        data["message"] = (
                            "Chrome ready aur WhatsApp already linked — AI auto-reply on"
                        )
                        return data
                except Exception as attach_exc:
                    logger.warning("WA Web post-launch attach skipped: %s", attach_exc)
                data["logged_in"] = False
                data["attached"] = False
                data["message"] = (
                    "Chrome khul gaya — is window mein Business link karo jab tak chats dikhen, "
                    "phir Connect / Start AI dabao"
                )
            return data
        except Exception as exc:
            logger.exception("WA Web launch Chrome failed")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=str(exc),
            ) from exc
