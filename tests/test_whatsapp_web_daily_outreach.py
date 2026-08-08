"""Unit tests for WhatsApp Web daily outreach lead selection (no Playwright)."""

from app.models.lead import Lead
from app.models.user import User, UserRole
from app.models.whatsapp_chat import WhatsAppChatMessage
from app.services.whatsapp_web.daily_outreach import pick_outreach_leads


def _user(db, email: str = "wa-daily@example.com") -> User:
    user = User(
        name="WA Daily",
        email=email,
        password_hash="x",
        role=UserRole.user,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _lead(db, user: User, **kwargs) -> Lead:
    defaults = {
        "user_id": user.id,
        "company_name": "Test Co",
        "phone": "923001111111",
        "is_saved": True,
        "city": "Lahore",
        "country": "Pakistan",
    }
    defaults.update(kwargs)
    lead = Lead(**defaults)
    db.add(lead)
    db.commit()
    db.refresh(lead)
    return lead


def test_pick_skips_no_phone_unsaved_and_already_outbound(db_session):
    owner = _user(db_session)
    eligible = _lead(db_session, owner, company_name="New Cafe", phone="923002222222")
    _lead(db_session, owner, company_name="No Phone", phone="")
    _lead(db_session, owner, company_name="Unsaved", phone="923003333333", is_saved=False)
    already = _lead(db_session, owner, company_name="Already", phone="923004444444")
    db_session.add(
        WhatsAppChatMessage(
            user_id=owner.id,
            lead_id=already.id,
            phone=already.phone,
            direction="outbound",
            body="Hi already sent",
        )
    )
    db_session.commit()

    picked = pick_outreach_leads(db_session, owner, limit=5)
    ids = {lead.id for lead in picked}
    assert eligible.id in ids
    assert already.id not in ids
    assert all((lead.phone or "").strip() for lead in picked)
    assert all(lead.is_saved for lead in picked)


def test_pick_prefers_newer_and_respects_limit(db_session):
    owner = _user(db_session, email="wa-daily-limit@example.com")
    older = _lead(db_session, owner, company_name="Older", phone="923005555555")
    newer = _lead(db_session, owner, company_name="Newer", phone="923006666666")
    picked = pick_outreach_leads(db_session, owner, limit=1)
    assert len(picked) == 1
    assert picked[0].id == newer.id
    assert picked[0].id != older.id
