"""Unit tests for WhatsApp Web queue/dedupe (no Playwright)."""

from app.models.whatsapp_web import WhatsAppWebInboundJob
from app.services.whatsapp_web.dedupe import make_dedupe_key
from app.services.whatsapp_web.queue import WhatsAppWebQueue


def test_dedupe_key_stable():
    a = make_dedupe_key(chat_title="Cafe", body="Hello", phone_hint="+92 300")
    b = make_dedupe_key(chat_title="Cafe", body="Hello", phone_hint="92300")
    assert a == b
    c = make_dedupe_key(chat_title="Cafe", body="Hi", phone_hint="92300")
    assert a != c


def test_queue_enqueue_dedupes(db_session):
    q = WhatsAppWebQueue(db_session)
    first = q.enqueue(chat_title="Shop", body="Need website", phone_hint="923001111111")
    second = q.enqueue(chat_title="Shop", body="Need website", phone_hint="923001111111")
    assert first is not None
    assert second is None
    assert db_session.query(WhatsAppWebInboundJob).count() == 1

    claimed = q.claim_next()
    assert claimed is not None
    assert claimed.status == "processing"
    q.mark_done(claimed, reply_body="Sure", ai_replied=True)
    assert claimed.status == "done"
