from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine


def ensure_lead_columns(engine: Engine) -> None:
    """Add new lead columns to existing SQLite DBs without full Alembic run."""
    inspector = inspect(engine)
    if "leads" not in inspector.get_table_names():
        return

    existing = {col["name"] for col in inspector.get_columns("leads")}
    additions = {
        "address": "VARCHAR(500)",
        "postal_code": "VARCHAR(20)",
        "category": "VARCHAR(255)",
        "quality_score": "INTEGER",
        "quality_tier": "VARCHAR(20)",
        "whatsapp_ready": "BOOLEAN",
        "is_saved": "BOOLEAN DEFAULT 0",
        "saved_at": "DATETIME",
        "phone_verified": "BOOLEAN",
        "email_verified": "BOOLEAN",
        "website_quality_score": "INTEGER",
        "website_opportunity_score": "INTEGER",
        "website_problems": "JSON",
        "reviews_count": "INTEGER",
        "rating": "REAL",
        "business_hours": "TEXT",
        "google_profile_score": "INTEGER",
        "photos_count": "INTEGER",
        "buying_intent_score": "INTEGER",
        "intent_tier": "VARCHAR(10)",
        "social_activity_score": "INTEGER",
        "social_links_verified": "BOOLEAN",
        "is_running_ads": "BOOLEAN",
        "ads_count": "INTEGER",
        "ad_platform": "VARCHAR(50)",
        "landing_page": "VARCHAR(500)",
        "ad_activity_score": "INTEGER",
        "ai_qualification": "VARCHAR(20)",
        "recommended_offer": "TEXT",
        "qualification_reason": "TEXT",
        "niche_key": "VARCHAR(50)",
        "recommended_service": "VARCHAR(255)",
        "intelligence_meta": "JSON",
    }

    with engine.begin() as conn:
        for column, col_type in additions.items():
            if column not in existing:
                conn.execute(text(f"ALTER TABLE leads ADD COLUMN {column} {col_type}"))


def ensure_user_google_columns(engine: Engine) -> None:
    """Add Google OAuth + token plan columns to users on existing DBs."""
    inspector = inspect(engine)
    if "users" not in inspector.get_table_names():
        return
    existing = {col["name"] for col in inspector.get_columns("users")}
    if "google_id" not in existing:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE users ADD COLUMN google_id VARCHAR(255)"))
            conn.execute(
                text("CREATE UNIQUE INDEX IF NOT EXISTS ix_users_google_id ON users (google_id)")
            )
    additions = {
        "avatar_url": "VARCHAR(500)",
        "api_access": "BOOLEAN DEFAULT 1",
        "plan": "VARCHAR(20) DEFAULT 'free'",
        "daily_token_limit": "INTEGER DEFAULT 50",
        "tokens_used_today": "INTEGER DEFAULT 0",
        "tokens_reset_on": "DATE",
        "own_api_keys_enabled": "BOOLEAN DEFAULT 0",
        "own_api_keys_requested": "BOOLEAN DEFAULT 0",
        "paid_plan_requested": "BOOLEAN DEFAULT 0",
    }
    with engine.begin() as conn:
        for column, col_type in additions.items():
            if column not in existing:
                conn.execute(text(f"ALTER TABLE users ADD COLUMN {column} {col_type}"))


def ensure_outreach_settings_columns(engine: Engine) -> None:
    """Add AI agent columns to email_outreach_settings on existing DBs."""
    inspector = inspect(engine)
    if "email_outreach_settings" not in inspector.get_table_names():
        return
    existing = {col["name"] for col in inspector.get_columns("email_outreach_settings")}
    additions = {
        "agent_running": "BOOLEAN DEFAULT 0",
        "agent_paused": "BOOLEAN DEFAULT 0",
        "auto_follow_up": "BOOLEAN DEFAULT 1",
        "working_hours_start": "INTEGER DEFAULT 9",
        "working_hours_end": "INTEGER DEFAULT 18",
        "weekends_enabled": "BOOLEAN DEFAULT 0",
        "standing_campaign_id": "INTEGER",
        "last_agent_run_at": "DATETIME",
        "ai_emails_generated": "INTEGER DEFAULT 0",
        "ai_replies_generated": "INTEGER DEFAULT 0",
        "agent_batch_delay_minutes": "INTEGER DEFAULT 10",
    }
    with engine.begin() as conn:
        for column, col_type in additions.items():
            if column not in existing:
                conn.execute(text(f"ALTER TABLE email_outreach_settings ADD COLUMN {column} {col_type}"))


def ensure_brain_columns(engine: Engine) -> None:
    """Add pricing + negotiation columns to brains on existing DBs."""
    inspector = inspect(engine)
    if "brains" not in inspector.get_table_names():
        return
    existing = {col["name"] for col in inspector.get_columns("brains")}
    additions = {
        "pricing_currency": "VARCHAR(10) DEFAULT 'USD'",
        "pricing_high": "REAL",
        "pricing_floor": "REAL",
    }
    with engine.begin() as conn:
        for column, col_type in additions.items():
            if column not in existing:
                conn.execute(text(f"ALTER TABLE brains ADD COLUMN {column} {col_type}"))


def ensure_conversation_columns(engine: Engine) -> None:
    """Add chat unread tracking columns to email_conversations."""
    inspector = inspect(engine)
    if "email_conversations" not in inspector.get_table_names():
        return
    existing = {col["name"] for col in inspector.get_columns("email_conversations")}
    additions = {
        "last_read_at": "DATETIME",
    }
    with engine.begin() as conn:
        for column, col_type in additions.items():
            if column not in existing:
                conn.execute(
                    text(f"ALTER TABLE email_conversations ADD COLUMN {column} {col_type}")
                )


def ensure_whatsapp_chat_columns(engine: Engine) -> None:
    """Add thread/phone columns to whatsapp_chat_messages on existing DBs."""
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    if "whatsapp_chat_messages" not in tables:
        return
    existing = {col["name"] for col in inspector.get_columns("whatsapp_chat_messages")}
    additions = {
        "thread_id": "INTEGER",
        "phone": "VARCHAR(40)",
    }
    with engine.begin() as conn:
        for column, col_type in additions.items():
            if column not in existing:
                conn.execute(
                    text(f"ALTER TABLE whatsapp_chat_messages ADD COLUMN {column} {col_type}")
                )
        if "thread_id" not in existing or "ix_whatsapp_chat_messages_thread_id" not in {
            ix["name"] for ix in inspector.get_indexes("whatsapp_chat_messages")
        }:
            try:
                conn.execute(
                    text(
                        "CREATE INDEX IF NOT EXISTS ix_whatsapp_chat_messages_thread_id "
                        "ON whatsapp_chat_messages (thread_id)"
                    )
                )
            except Exception:
                pass
            try:
                conn.execute(
                    text(
                        "CREATE INDEX IF NOT EXISTS ix_whatsapp_chat_messages_phone "
                        "ON whatsapp_chat_messages (phone)"
                    )
                )
            except Exception:
                pass

