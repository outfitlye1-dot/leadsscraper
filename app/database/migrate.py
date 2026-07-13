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

