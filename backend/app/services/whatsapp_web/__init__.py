"""WhatsApp Web (Playwright) — optional automation, separate from Cloud API.

This package must NOT modify or depend on Meta Cloud webhook/send paths.
Enable only via WA_WEB_ENABLED=true.
"""

from app.services.whatsapp_web.service import WhatsAppWebService

__all__ = ["WhatsAppWebService"]
