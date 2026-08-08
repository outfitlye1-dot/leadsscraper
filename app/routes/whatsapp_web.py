"""WhatsApp Web (Playwright) control APIs — does not touch Cloud API routes.

Playwright Sync API must never run on the asyncio event-loop thread. All browser
work is offloaded with ``asyncio.to_thread``.
"""

from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, Depends, Query

from app.core.auth import get_current_user
from app.models.user import User
from app.schemas.whatsapp_web import (
    WhatsAppWebJobItem,
    WhatsAppWebLaunchChromeResponse,
    WhatsAppWebPairCodeRequest,
    WhatsAppWebPairCodeResponse,
    WhatsAppWebQrResponse,
    WhatsAppWebReconnectResponse,
    WhatsAppWebSettingsResponse,
    WhatsAppWebSettingsUpdateRequest,
    WhatsAppWebStartResponse,
    WhatsAppWebStatusResponse,
)
from app.services.whatsapp_web import WhatsAppWebService

router = APIRouter(prefix="/api/whatsapp-web", tags=["whatsapp-web"])


async def _to_thread(fn, /, *args: Any, **kwargs: Any) -> Any:
    return await asyncio.to_thread(fn, *args, **kwargs)


@router.get("/status", response_model=WhatsAppWebStatusResponse)
async def whatsapp_web_status(
    current_user: User = Depends(get_current_user),
) -> WhatsAppWebStatusResponse:
    _ = current_user
    data = await _to_thread(lambda: WhatsAppWebService().status())
    return WhatsAppWebStatusResponse(**data)


@router.get("/qr", response_model=WhatsAppWebQrResponse)
async def whatsapp_web_qr(
    current_user: User = Depends(get_current_user),
) -> WhatsAppWebQrResponse:
    data = await _to_thread(lambda: WhatsAppWebService().get_qr(user=current_user))
    return WhatsAppWebQrResponse(**data)


@router.post("/reconnect", response_model=WhatsAppWebReconnectResponse)
async def whatsapp_web_reconnect(
    current_user: User = Depends(get_current_user),
) -> WhatsAppWebReconnectResponse:
    data = await _to_thread(lambda: WhatsAppWebService().reconnect(user=current_user))
    return WhatsAppWebReconnectResponse(**data)


@router.post("/reset", response_model=WhatsAppWebStartResponse)
async def whatsapp_web_reset(
    current_user: User = Depends(get_current_user),
) -> WhatsAppWebStartResponse:
    """Clear profile + fresh QR — use after Business 'Couldn't link'."""
    data = await _to_thread(lambda: WhatsAppWebService().reset_session(user=current_user))
    return WhatsAppWebStartResponse(**data)


@router.post("/pair-code", response_model=WhatsAppWebPairCodeResponse)
async def whatsapp_web_pair_code(
    data: WhatsAppWebPairCodeRequest,
    current_user: User = Depends(get_current_user),
) -> WhatsAppWebPairCodeResponse:
    """Alternative to QR for WhatsApp Business linking."""
    result = await _to_thread(
        lambda: WhatsAppWebService().request_pair_code(data.phone, user=current_user)
    )
    return WhatsAppWebPairCodeResponse(**result)


@router.post("/pair-code/read", response_model=WhatsAppWebPairCodeResponse)
async def whatsapp_web_read_pair_code(
    current_user: User = Depends(get_current_user),
) -> WhatsAppWebPairCodeResponse:
    """Read pairing code already visible in the Chrome WhatsApp window."""
    result = await _to_thread(lambda: WhatsAppWebService().read_pair_code(user=current_user))
    return WhatsAppWebPairCodeResponse(**result)


@router.post("/launch-chrome", response_model=WhatsAppWebLaunchChromeResponse)
async def whatsapp_web_launch_chrome(
    current_user: User = Depends(get_current_user),
) -> WhatsAppWebLaunchChromeResponse:
    """Open real Chrome (port 9222) for WhatsApp Business linking."""
    _ = current_user
    data = await _to_thread(lambda: WhatsAppWebService().launch_chrome())
    return WhatsAppWebLaunchChromeResponse(**data)


@router.post("/start", response_model=WhatsAppWebStartResponse)
async def whatsapp_web_start(
    current_user: User = Depends(get_current_user),
) -> WhatsAppWebStartResponse:
    """Connect WhatsApp Web (QR if needed) and start AI auto-reply for this login user."""
    data = await _to_thread(lambda: WhatsAppWebService().start_automation(user=current_user))
    return WhatsAppWebStartResponse(**data)


@router.post("/stop", response_model=WhatsAppWebStartResponse)
async def whatsapp_web_stop(
    current_user: User = Depends(get_current_user),
) -> WhatsAppWebStartResponse:
    _ = current_user
    data = await _to_thread(lambda: WhatsAppWebService().stop_automation())
    return WhatsAppWebStartResponse(
        ok=True,
        logged_in=False,
        worker_running=bool(data.get("worker_running")),
        message=data.get("message"),
    )


@router.get("/jobs", response_model=list[WhatsAppWebJobItem])
async def whatsapp_web_jobs(
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
) -> list[WhatsAppWebJobItem]:
    _ = current_user
    rows = await _to_thread(lambda: WhatsAppWebService().list_jobs(limit=limit))
    return [WhatsAppWebJobItem(**row) for row in rows]


@router.get("/settings", response_model=WhatsAppWebSettingsResponse)
async def whatsapp_web_get_settings(
    current_user: User = Depends(get_current_user),
) -> WhatsAppWebSettingsResponse:
    _ = current_user
    data = await _to_thread(lambda: WhatsAppWebService().get_settings())
    return WhatsAppWebSettingsResponse(**data)


@router.put("/settings", response_model=WhatsAppWebSettingsResponse)
async def whatsapp_web_update_settings(
    data: WhatsAppWebSettingsUpdateRequest,
    current_user: User = Depends(get_current_user),
) -> WhatsAppWebSettingsResponse:
    _ = current_user
    payload = data.model_dump(exclude_none=True)
    result = await _to_thread(lambda: WhatsAppWebService().update_settings(**payload))
    return WhatsAppWebSettingsResponse(**result)
