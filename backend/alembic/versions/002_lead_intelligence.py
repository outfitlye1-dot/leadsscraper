"""002 — Lead intelligence columns for AI Sales Intelligence Engine."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002_lead_intelligence"
down_revision: Union[str, None] = "001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    cols = [
        ("phone_verified", sa.Boolean()),
        ("email_verified", sa.Boolean()),
        ("website_quality_score", sa.Integer()),
        ("website_opportunity_score", sa.Integer()),
        ("website_problems", sa.JSON()),
        ("reviews_count", sa.Integer()),
        ("rating", sa.Float()),
        ("business_hours", sa.Text()),
        ("google_profile_score", sa.Integer()),
        ("photos_count", sa.Integer()),
        ("buying_intent_score", sa.Integer()),
        ("intent_tier", sa.String(length=10)),
        ("social_activity_score", sa.Integer()),
        ("social_links_verified", sa.Boolean()),
        ("is_running_ads", sa.Boolean()),
        ("ads_count", sa.Integer()),
        ("ad_platform", sa.String(length=50)),
        ("landing_page", sa.String(length=500)),
        ("ad_activity_score", sa.Integer()),
        ("ai_qualification", sa.String(length=20)),
        ("recommended_offer", sa.Text()),
        ("qualification_reason", sa.Text()),
        ("niche_key", sa.String(length=50)),
        ("recommended_service", sa.String(length=255)),
        ("intelligence_meta", sa.JSON()),
    ]
    for name, col_type in cols:
        op.add_column("leads", sa.Column(name, col_type, nullable=True))
    op.create_index("ix_leads_intent_tier", "leads", ["intent_tier"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_leads_intent_tier", table_name="leads")
    for name, _ in reversed(
        [
            ("intelligence_meta", None),
            ("recommended_service", None),
            ("niche_key", None),
            ("qualification_reason", None),
            ("recommended_offer", None),
            ("ai_qualification", None),
            ("ad_activity_score", None),
            ("landing_page", None),
            ("ad_platform", None),
            ("ads_count", None),
            ("is_running_ads", None),
            ("social_links_verified", None),
            ("social_activity_score", None),
            ("intent_tier", None),
            ("buying_intent_score", None),
            ("photos_count", None),
            ("google_profile_score", None),
            ("business_hours", None),
            ("rating", None),
            ("reviews_count", None),
            ("website_problems", None),
            ("website_opportunity_score", None),
            ("website_quality_score", None),
            ("email_verified", None),
            ("phone_verified", None),
        ]
    ):
        op.drop_column("leads", name)
