"""Unit tests for WhatsApp Web settings store (no Playwright required)."""

from pathlib import Path

from app.services.whatsapp_web.settings_store import WhatsAppWebSettingsStore


def test_settings_store_defaults_and_update(tmp_path: Path):
    store = WhatsAppWebSettingsStore(path=tmp_path / "wa_web_settings.json")
    data = store.get_all()
    assert data["auto_reply"] is True
    assert data["ignore_groups"] is True
    assert data["ignore_phones"] == []

    updated = store.update(auto_reply=False, ignore_phones=["923001234567"])
    assert updated["auto_reply"] is False
    assert updated["ignore_phones"] == ["923001234567"]

    again = WhatsAppWebSettingsStore(path=tmp_path / "wa_web_settings.json")
    loaded = again.get_all()
    assert loaded["auto_reply"] is False
    assert again.is_phone_ignored("+92 300 1234567") is True
    assert again.is_phone_ignored("999") is False


def test_human_takeover_match(tmp_path: Path):
    store = WhatsAppWebSettingsStore(path=tmp_path / "settings.json")
    store.update(human_takeover_phones=["3001234567"])
    assert store.is_human_takeover("923001234567") is True
    assert store.is_human_takeover("911") is False


def test_set_owner_from_login(tmp_path: Path):
    store = WhatsAppWebSettingsStore(path=tmp_path / "settings.json")
    assert store.get_owner_user_id() is None
    store.set_owner(42, "user@example.com")
    assert store.get_owner_user_id() == 42
    assert store.get_all()["owner_email"] == "user@example.com"


def test_daily_outreach_defaults_and_clamp(tmp_path: Path):
    store = WhatsAppWebSettingsStore(path=tmp_path / "settings.json")
    data = store.get_all()
    assert data["daily_outreach_enabled"] is False
    assert data["daily_outreach_limit"] == 5
    assert data["daily_outreach_sent_count"] == 0

    updated = store.update(daily_outreach_enabled=True, daily_outreach_limit=99)
    assert updated["daily_outreach_enabled"] is True
    assert updated["daily_outreach_limit"] == 10

    updated = store.update(daily_outreach_limit=0)
    assert updated["daily_outreach_limit"] == 1


def test_daily_outreach_quota_and_record(tmp_path: Path):
    from datetime import UTC, datetime, timedelta

    store = WhatsAppWebSettingsStore(path=tmp_path / "settings.json")
    store.update(daily_outreach_enabled=True, daily_outreach_limit=2)

    q = store.daily_outreach_quota()
    assert q["enabled"] is True
    assert q["limit"] == 2
    assert q["sent_count"] == 0
    assert q["remaining"] == 2
    assert q["interval_minutes"] == 60
    assert q["ready"] is True
    assert q["sent_date"] == datetime.now(UTC).strftime("%Y-%m-%d")

    after1 = store.record_daily_outreach_send()
    assert after1["sent_count"] == 1
    assert after1["remaining"] == 1
    assert after1["ready"] is False

    q2 = store.daily_outreach_quota()
    assert q2["ready"] is False
    assert q2["seconds_until_next"] > 0

    # Simulate last attempt ~61 minutes ago → ready again
    past = (datetime.now(UTC) - timedelta(minutes=61)).isoformat()
    store.update(daily_outreach_last_attempt_at=past)
    assert store.daily_outreach_quota()["ready"] is True

    after2 = store.record_daily_outreach_send()
    assert after2["sent_count"] == 2
    assert after2["remaining"] == 0

    # Stale date resets count
    store.update(daily_outreach_sent_date="2000-01-01", daily_outreach_sent_count=9)
    reset = store.daily_outreach_quota()
    assert reset["sent_count"] == 0
    assert reset["remaining"] == 2


def test_png_from_data_ref_renders():
    from app.services.whatsapp_web.session import _png_from_data_ref

    # Fake WhatsApp-like ref payload
    ref = "2@" + ("A" * 80) + ",1,2,3"
    png = _png_from_data_ref(ref)
    assert png is not None
    assert png[:8] == b"\x89PNG\r\n\x1a\n"
    assert _png_from_data_ref("short") is None

