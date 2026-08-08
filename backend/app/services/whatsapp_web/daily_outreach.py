"""Daily WhatsApp Web outreach: pick saved leads, AI opener, send via Playwright."""

from __future__ import annotations

import logging
import time
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.lead import Lead
from app.models.user import User
from app.models.whatsapp_chat import WhatsAppChatMessage
from app.services.whatsapp_chat_service import WhatsAppChatService
from app.services.whatsapp_web.sender import normalize_search_target, send_text
from app.services.whatsapp_web.settings_store import WhatsAppWebSettingsStore
from app.utils.outreach_tone import sanitize_paid_outreach_message

logger = logging.getLogger(__name__)


def pick_outreach_leads(
    db: Session,
    owner: User,
    *,
    limit: int = 1,
) -> list[Lead]:
    """Saved leads with phone, never messaged outbound on WhatsApp for this user."""
    if limit <= 0:
        return []

    already = {
        row[0]
        for row in (
            db.query(WhatsAppChatMessage.lead_id)
            .filter(
                WhatsAppChatMessage.user_id == owner.id,
                WhatsAppChatMessage.direction == "outbound",
                WhatsAppChatMessage.lead_id.isnot(None),
            )
            .distinct()
            .all()
        )
        if row[0] is not None
    }

    candidates = (
        db.query(Lead)
        .filter(
            Lead.user_id == owner.id,
            Lead.is_saved.is_(True),
            Lead.phone.isnot(None),
            Lead.phone != "",
        )
        .order_by(Lead.id.desc())
        .limit(400)
        .all()
    )

    picked: list[Lead] = []
    for lead in candidates:
        if lead.id in already:
            continue
        phone = (lead.phone or "").strip()
        if not phone:
            continue
        picked.append(lead)
        if len(picked) >= limit:
            break
    return picked


def generate_english_opener(db: Session, owner: User, lead: Lead) -> str:
    """Lead-aware AI opener forced to English; falls back to a short English line."""
    chat = WhatsAppChatService(db)
    phone = (lead.phone or "").strip()
    try:
        text = chat._generate_opener(owner, lead, phone, force_english=True)
    except Exception as exc:
        logger.warning(
            "Daily WA outreach opener AI failed lead=%s: %s",
            lead.id,
            exc,
        )
        company = lead.company_name or "your business"
        place = ", ".join(p for p in [lead.city, lead.country] if p)
        if place:
            text = (
                f"Hi, I came across {company} in {place} and help local businesses "
                f"with websites and online presence. Open to a quick chat?"
            )
        else:
            text = (
                f"Hi, I saw {company} and help local businesses with websites "
                f"and online presence. Open to a quick chat?"
            )
        text = sanitize_paid_outreach_message(text)
    return (text or "").strip()


def persist_outbound_opener(
    db: Session,
    owner: User,
    lead: Lead,
    body: str,
) -> WhatsAppChatMessage:
    """Log outbound so UI + dedupe skip this lead next time."""
    chat = WhatsAppChatService(db)
    thread = chat._get_or_create_thread(owner, lead)
    msg = chat._save(
        owner.id,
        lead.id,
        "outbound",
        body,
        thread=thread,
        phone=thread.phone,
        commit=False,
    )
    chat._refresh_thread_memory(thread, outbound_text=body)
    if not thread.deal_status or thread.deal_status == "new":
        thread.deal_status = "open"
    db.commit()
    db.refresh(msg)
    return msg


def run_one_daily_outreach(
    db: Session,
    owner: User,
    settings_store: WhatsAppWebSettingsStore,
) -> dict[str, Any] | None:
    """Send one personalized opener if quota remains. Returns result dict or None."""
    quota = settings_store.daily_outreach_quota()
    if not quota.get("enabled"):
        return None
    if int(quota.get("remaining") or 0) <= 0:
        return None
    if not quota.get("ready", True):
        logger.debug(
            "Daily WA outreach: waiting %ss until next send",
            quota.get("seconds_until_next"),
        )
        return None

    leads = pick_outreach_leads(db, owner, limit=1)
    if not leads:
        logger.info("Daily WA outreach: no eligible saved leads for user=%s", owner.id)
        return None

    lead = leads[0]
    phone = (lead.phone or "").strip()
    if settings_store.is_phone_ignored(phone) or settings_store.is_human_takeover(phone):
        logger.info(
            "Daily WA outreach: skip lead=%s (ignore/takeover phone …%s)",
            lead.id,
            phone[-4:] if phone else "",
        )
        return {"skipped": True, "lead_id": lead.id, "reason": "ignore_or_takeover"}

    body = generate_english_opener(db, owner, lead)
    if not body:
        return {"skipped": True, "lead_id": lead.id, "reason": "empty_opener"}

    search = normalize_search_target(phone, lead.company_name or lead.contact_name or "")
    typing_ms = int(get_settings().WA_WEB_TYPING_DELAY_MS or 40)
    try:
        send_text(search_query=search, body=body, typing_delay_ms=typing_ms)
    except Exception as exc:
        # Cool down even on failure so we don't hammer WhatsApp every few seconds
        settings_store.record_daily_outreach_attempt()
        logger.warning(
            "Daily WA outreach send failed lead=%s: %s",
            lead.id,
            exc,
        )
        return {
            "ok": False,
            "lead_id": lead.id,
            "error": str(exc),
        }

    # Brief pause after send to reduce ban risk
    time.sleep(1.5)

    try:
        persist_outbound_opener(db, owner, lead, body)
    except Exception:
        logger.exception(
            "Daily WA outreach: sent but failed to persist message lead=%s",
            lead.id,
        )

    new_quota = settings_store.record_daily_outreach_send()
    logger.info(
        "Daily WA outreach sent lead=%s company=%r sent_today=%s/%s",
        lead.id,
        (lead.company_name or "")[:40],
        new_quota.get("sent_count"),
        new_quota.get("limit"),
    )
    return {
        "ok": True,
        "lead_id": lead.id,
        "phone": phone,
        "body": body[:200],
        "quota": new_quota,
    }
