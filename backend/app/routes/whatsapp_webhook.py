"""Meta WhatsApp Cloud API webhooks — verify + inbound messages."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.database.database import get_db
from app.services.whatsapp_chat_service import WhatsAppChatService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/whatsapp-webhook", tags=["whatsapp-webhook"])


@router.get("")
@router.get("/")
def verify_whatsapp_webhook(
    hub_mode: str | None = Query(None, alias="hub.mode"),
    hub_verify_token: str | None = Query(None, alias="hub.verify_token"),
    hub_challenge: str | None = Query(None, alias="hub.challenge"),
) -> Response:
    """Meta subscription verification handshake."""
    settings = get_settings()
    expected = (settings.WHATSAPP_VERIFY_TOKEN or "").strip()
    got = (hub_verify_token or "").strip()
    if hub_mode == "subscribe" and expected and got == expected and hub_challenge:
        return Response(content=str(hub_challenge), media_type="text/plain")

    logger.warning(
        "WhatsApp webhook verify failed mode=%r token_match=%s challenge=%s",
        hub_mode,
        bool(got) and got == expected,
        bool(hub_challenge),
    )
    # Meta shows this body when Verify Token in dashboard != WHATSAPP_VERIFY_TOKEN
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=(
            "Webhook verification failed. "
            f"Use Callback URL …/api/whatsapp-webhook and Verify token exactly: {expected or '(set WHATSAPP_VERIFY_TOKEN)'}"
        ),
    )


@router.post("")
@router.post("/")
async def receive_whatsapp_webhook(
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """Receive inbound messages / status updates from Meta."""
    try:
        payload: dict[str, Any] = await request.json()
    except Exception:
        return {"status": "ignored"}

    try:
        result = WhatsAppChatService(db).ingest_cloud_webhook(payload)
        logger.info("WhatsApp webhook ingested: %s", result)
    except Exception as exc:
        # Always ACK Meta quickly — log and continue
        logger.warning("WhatsApp webhook processing failed: %s", exc)
    return {"status": "ok"}
