"""Background worker: poll WhatsApp Web → queue → AI reply → send.

Does not touch Meta Cloud API paths.
"""

from __future__ import annotations

import logging
import re
import threading
import time
from collections import deque

from app.core.config import get_settings
from app.database.database import SessionLocal
from app.models.lead import Lead
from app.models.user import User, UserRole
from app.services.whatsapp_chat_service import WhatsAppChatService
from app.services.whatsapp_web import session as wa_session
from app.services.whatsapp_web.browser import wa_web_browser
from app.services.whatsapp_web.daily_outreach import run_one_daily_outreach
from app.services.whatsapp_web.listener import poll_unread_and_collect
from app.services.whatsapp_web.queue import WhatsAppWebQueue
from app.services.whatsapp_web.sender import normalize_search_target, send_text
from app.services.whatsapp_web.settings_store import WhatsAppWebSettingsStore

logger = logging.getLogger(__name__)


class WhatsAppWebWorker:
    def __init__(self) -> None:
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._send_times: deque[float] = deque(maxlen=60)
        self._settings = WhatsAppWebSettingsStore()
        self._last_cdp_attach_attempt = 0.0

    def start(self) -> None:
        settings = get_settings()
        if not settings.WA_WEB_ENABLED:
            logger.info("WhatsApp Web worker not started (WA_WEB_ENABLED=false)")
            return
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run_loop, daemon=True, name="wa-web-worker")
        self._thread.start()
        logger.info("WhatsApp Web worker started")

    def stop(self) -> None:
        self._stop.set()

    def is_running(self) -> bool:
        return bool(self._thread and self._thread.is_alive())

    def _resolve_owner(self, db) -> User | None:
        # 1) Frontend Connect binds logged-in user into settings store
        bound_id = self._settings.get_owner_user_id()
        if bound_id:
            user = db.query(User).filter(User.id == int(bound_id)).first()
            if user:
                return user
        # 2) Optional .env overrides (legacy / server-only)
        settings = get_settings()
        if settings.WA_WEB_USER_ID:
            user = db.query(User).filter(User.id == int(settings.WA_WEB_USER_ID)).first()
            if user:
                return user
        email = (settings.WA_WEB_USER_EMAIL or settings.ADMIN_EMAIL or "").strip().lower()
        if email:
            user = db.query(User).filter(User.email == email).first()
            if user:
                return user
        return (
            db.query(User)
            .filter(User.role == UserRole.admin)
            .order_by(User.id.asc())
            .first()
        )

    def _match_lead(self, db, owner: User, phone_hint: str | None, chat_title: str) -> Lead | None:
        digits = re.sub(r"\D", "", phone_hint or "")
        chat = WhatsAppChatService(db)
        if digits:
            # Prefer owner's saved lead with matching phone
            leads = (
                db.query(Lead)
                .filter(
                    Lead.user_id == owner.id,
                    Lead.is_saved.is_(True),
                    Lead.phone.isnot(None),
                    Lead.phone != "",
                )
                .order_by(Lead.id.desc())
                .limit(500)
                .all()
            )
            for lead in leads:
                if chat._phone_digits_match(lead.phone or "", digits):
                    return lead
            # Fallback: global matcher then verify ownership
            found = chat._find_lead_by_phone_digits(digits)
            if found and int(found.user_id) == int(owner.id):
                return found

        title = (chat_title or "").strip().lower()
        if len(title) >= 3:
            leads = (
                db.query(Lead)
                .filter(Lead.user_id == owner.id, Lead.is_saved.is_(True))
                .order_by(Lead.id.desc())
                .limit(400)
                .all()
            )
            for lead in leads:
                company = (lead.company_name or "").strip().lower()
                contact = (lead.contact_name or "").strip().lower()
                if company and (company in title or title in company):
                    return lead
                if contact and len(contact) >= 3 and (contact == title or contact in title or title in contact):
                    return lead
        return None

    def _rate_limit_ok(self) -> bool:
        settings = get_settings()
        limit = max(1, int(settings.WA_WEB_MAX_REPLIES_PER_MIN or 8))
        now = time.monotonic()
        while self._send_times and now - self._send_times[0] > 60:
            self._send_times.popleft()
        return len(self._send_times) < limit

    def _run_loop(self) -> None:
        while not self._stop.is_set():
            settings = get_settings()
            poll = max(2, int(settings.WA_WEB_POLL_SECONDS or 3))
            if not settings.WA_WEB_ENABLED:
                time.sleep(poll)
                continue
            try:
                self._tick()
            except Exception:
                logger.exception("WA Web worker tick failed")
            time.sleep(poll)

    def _tick(self) -> None:
        store = self._settings.get_all()
        settings = get_settings()
        # After uvicorn --reload, Playwright attach is lost but Chrome CDP often
        # still has WhatsApp linked — soft reattach so status stays "Linked".
        if not wa_web_browser.is_started():
            cdp = (settings.WA_WEB_CDP_URL or "").strip()
            now = time.monotonic()
            if cdp and now - self._last_cdp_attach_attempt >= 20.0:
                self._last_cdp_attach_attempt = now
                if wa_web_browser.is_cdp_alive(timeout_seconds=1.0):
                    try:
                        logger.info("WA Web worker: auto-reattach to live Chrome CDP")
                        info = wa_session.ensure_session(navigate=True, settle_seconds=1.0)
                        if info.get("logged_in"):
                            logger.info("WA Web worker: CDP reattached — chats linked")
                        else:
                            logger.info(
                                "WA Web worker: CDP attached but chats not detected yet"
                            )
                    except Exception as exc:
                        logger.warning("WA Web worker auto-reattach failed: %s", exc)
            if not wa_web_browser.is_started():
                return
        try:
            if not wa_session.is_logged_in():
                return
        except Exception as exc:
            logger.warning("WA Web login check failed: %s", exc)
            return

        # 1) Detect + enqueue
        try:
            items = poll_unread_and_collect(max_chats=5)
        except TimeoutError:
            logger.debug("WA Web listener skipped — browser busy")
            items = []
        except Exception:
            logger.exception("WA Web listener failed")
            items = []

        if items:
            db = SessionLocal()
            try:
                queue = WhatsAppWebQueue(db)
                for item in items:
                    if store.get("ignore_groups") and "group" in (item.get("chat_title") or "").lower():
                        continue
                    phone = item.get("phone_hint") or ""
                    if phone and self._settings.is_phone_ignored(phone):
                        logger.info("WA Web ignored phone ending …%s", phone[-4:])
                        continue
                    queue.enqueue(
                        chat_title=item.get("chat_title") or "",
                        body=item.get("body") or "",
                        phone_hint=phone or None,
                    )
            finally:
                db.close()

        # 2) Process inbound queue with AI + send (one job per tick)
        sent_this_tick = False
        if store.get("auto_reply", True) and self._rate_limit_ok():
            sent_this_tick = self._process_one_auto_reply()
        elif store.get("auto_reply", True) and not self._rate_limit_ok():
            logger.info("WA Web rate limit — skipping auto-reply this tick")

        # 3) Daily outreach to saved leads (1 per tick, separate from inbound)
        if not sent_this_tick and self._rate_limit_ok():
            self._daily_outreach_tick()

    def _process_one_auto_reply(self) -> bool:
        """Claim one inbound job, AI reply, send. Returns True if a message was sent."""
        db = SessionLocal()
        try:
            owner = self._resolve_owner(db)
            if not owner:
                logger.warning(
                    "WA Web: no owner user — open Settings → WhatsApp Web and click Connect while logged in"
                )
                return False
            queue = WhatsAppWebQueue(db)
            job = queue.claim_next()
            if not job:
                return False

            phone = job.phone_hint or ""
            if phone and self._settings.is_human_takeover(phone):
                queue.mark_skipped(job, "human_takeover")
                return False
            if phone and self._settings.is_phone_ignored(phone):
                queue.mark_skipped(job, "ignored_phone")
                return False

            lead = self._match_lead(db, owner, job.phone_hint, job.chat_title)
            reply_text: str
            lead_id: int | None = None
            try:
                chat_svc = WhatsAppChatService(db)
                history = ""
                if not lead:
                    history = queue.chat_history_text(
                        chat_title=job.chat_title or "",
                        phone_hint=job.phone_hint,
                        exclude_job_id=int(job.id),
                        limit=4,
                    )
                reply_text, mode, lead_id = chat_svc.compose_web_auto_reply(
                    owner,
                    customer_message=job.body,
                    chat_title=job.chat_title or "",
                    phone_hint=job.phone_hint,
                    lead=lead,
                    history=history,
                )
                logger.info(
                    "WA Web auto-reply job=%s mode=%s lead=%s title=%r msg=%r",
                    job.id,
                    mode,
                    lead_id,
                    (job.chat_title or "")[:40],
                    (job.body or "")[:60],
                )
            except Exception as exc:
                logger.exception("WA Web AI reply failed job=%s", job.id)
                queue.mark_failed(job, f"ai_error: {exc}")
                return False

            search = normalize_search_target(job.phone_hint, job.chat_title)
            try:
                send_text(
                    search_query=search,
                    body=reply_text,
                    typing_delay_ms=int(get_settings().WA_WEB_TYPING_DELAY_MS or 40),
                )
                self._send_times.append(time.monotonic())
                queue.mark_done(
                    job,
                    reply_body=reply_text,
                    lead_id=lead_id,
                    user_id=int(owner.id),
                    ai_replied=True,
                )
                return True
            except Exception as exc:
                logger.exception("WA Web send failed job=%s", job.id)
                queue.mark_failed(job, f"send_error: {exc}")
                return False
        finally:
            db.close()

    def _daily_outreach_tick(self) -> None:
        """Send one personalized English opener to a saved lead if quota remains."""
        quota = self._settings.daily_outreach_quota()
        if not quota.get("enabled"):
            return
        if int(quota.get("remaining") or 0) <= 0:
            return

        db = SessionLocal()
        try:
            owner = self._resolve_owner(db)
            if not owner:
                return
            result = run_one_daily_outreach(db, owner, self._settings)
            if result and result.get("ok"):
                self._send_times.append(time.monotonic())
        except Exception:
            logger.exception("WA Web daily outreach tick failed")
        finally:
            db.close()


wa_web_worker = WhatsAppWebWorker()
