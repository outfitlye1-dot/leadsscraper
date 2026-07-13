from datetime import UTC, datetime

from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session

from app.models.lead import Lead, LeadStatus


class LeadRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, user_id: int, data: dict) -> Lead:
        lead = Lead(user_id=user_id, **data)
        self.db.add(lead)
        self.db.commit()
        self.db.refresh(lead)
        return lead

    def bulk_create(self, user_id: int, leads_data: list[dict]) -> list[Lead]:
        if not leads_data:
            return []
        leads = [Lead(user_id=user_id, **data) for data in leads_data]
        self.db.add_all(leads)
        self.db.commit()
        for lead in leads:
            self.db.refresh(lead)
        return leads

    def get_all_for_user_light(self, user_id: int) -> list[Lead]:
        """Load minimal columns for duplicate detection."""
        return (
            self.db.query(Lead)
            .filter(Lead.user_id == user_id)
            .order_by(Lead.created_at.desc())
            .all()
        )

    def get_by_id(self, user_id: int, lead_id: int) -> Lead | None:
        return (
            self.db.query(Lead)
            .filter(Lead.id == lead_id, Lead.user_id == user_id)
            .first()
        )

    def update(self, lead: Lead, data: dict) -> Lead:
        for key, value in data.items():
            if value is not None:
                setattr(lead, key, value)
        self.db.commit()
        self.db.refresh(lead)
        return lead

    def delete(self, lead: Lead) -> None:
        self.db.delete(lead)
        self.db.commit()

    def _filtered_query(
        self,
        user_id: int,
        q: str | None = None,
        city: str | None = None,
        country: str | None = None,
        industry: str | None = None,
        status: LeadStatus | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        source: str | None = None,
        quality_tier: str | None = None,
        whatsapp_ready: bool | None = None,
        has_email: bool | None = None,
        has_website: bool | None = None,
        saved: bool | None = None,
        include_background: bool = False,
    ):
        query = self.db.query(Lead).filter(Lead.user_id == user_id)

        if saved is True:
            query = query.filter(Lead.is_saved.is_(True))
        elif saved is False:
            query = query.filter(or_(Lead.is_saved.is_(False), Lead.is_saved.is_(None)))

        if q:
            pattern = f"%{q}%"
            query = query.filter(
                or_(
                    Lead.company_name.ilike(pattern),
                    Lead.contact_name.ilike(pattern),
                    Lead.phone.ilike(pattern),
                    Lead.email.ilike(pattern),
                    Lead.website.ilike(pattern),
                    Lead.category.ilike(pattern),
                    Lead.notes.ilike(pattern),
                )
            )
        if city:
            query = query.filter(Lead.city.ilike(f"%{city}%"))
        if country:
            query = query.filter(Lead.country.ilike(f"%{country}%"))
        if industry:
            query = query.filter(Lead.industry.ilike(f"%{industry}%"))
        if source:
            query = query.filter(Lead.source.ilike(f"%{source}%"))
        if quality_tier:
            query = query.filter(Lead.quality_tier == quality_tier.lower())
        if status:
            query = query.filter(Lead.status == status)
        if whatsapp_ready is True:
            query = query.filter(Lead.whatsapp_ready.is_(True))
        elif whatsapp_ready is False:
            query = query.filter(or_(Lead.whatsapp_ready.is_(False), Lead.whatsapp_ready.is_(None)))
        if has_email is True:
            query = query.filter(Lead.email.isnot(None), Lead.email != "")
        elif has_email is False:
            query = query.filter(or_(Lead.email.is_(None), Lead.email == ""))
        if has_website is True:
            query = query.filter(Lead.website.isnot(None), Lead.website != "")
        elif has_website is False:
            query = query.filter(or_(Lead.website.is_(None), Lead.website == ""))
        if date_from:
            query = query.filter(Lead.created_at >= date_from)
        if date_to:
            query = query.filter(Lead.created_at <= date_to)

        if not include_background:
            query = query.filter(self._exclude_background_filter())

        return query

    def _only_background_filter(self):
        flag = func.json_extract(Lead.intelligence_meta, "$.scrape_context.background")
        return or_(flag == 1, flag == True, flag == "true")  # noqa: E712

    def _exclude_background_filter(self):
        flag = func.json_extract(Lead.intelligence_meta, "$.scrape_context.background")
        return or_(
            Lead.intelligence_meta.is_(None),
            flag.is_(None),
            and_(flag != 1, flag != True, flag != "true"),  # noqa: E712
        )

    def find_background_for_scrape_request(self, user_id: int, data, limit: int) -> list[Lead]:
        from app.utils.scrape_context import lead_matches_scrape_request

        candidates = (
            self.db.query(Lead)
            .filter(Lead.user_id == user_id, self._only_background_filter())
            .order_by(Lead.created_at.desc())
            .limit(max(limit * 8, 200))
            .all()
        )
        matched = [lead for lead in candidates if lead_matches_scrape_request(lead, data)]
        return matched[:limit]

    def promote_background_leads(self, user_id: int, lead_ids: list[int]) -> int:
        if not lead_ids:
            return 0
        leads = self.get_many_by_ids(user_id, lead_ids)
        promoted = 0
        for lead in leads:
            meta = lead.intelligence_meta if isinstance(lead.intelligence_meta, dict) else {}
            ctx = meta.get("scrape_context") if isinstance(meta.get("scrape_context"), dict) else {}
            if not ctx.get("background"):
                continue
            ctx = dict(ctx)
            ctx["background"] = False
            ctx["promoted_from_cache"] = True
            meta = dict(meta)
            meta["scrape_context"] = ctx
            lead.intelligence_meta = meta
            promoted += 1
        if promoted:
            self.db.commit()
        return promoted

    def find_for_scrape_request(self, user_id: int, data, limit: int) -> list[Lead]:
        return self.find_background_for_scrape_request(user_id, data, limit)

    def delete_by_ids(self, user_id: int, lead_ids: list[int], *, saved: bool | None = None) -> int:
        if not lead_ids:
            return 0
        query = self._filtered_query(user_id, saved=saved).filter(Lead.id.in_(lead_ids))
        count = query.delete(synchronize_session=False)
        self.db.commit()
        return count

    def delete_inbox_by_ids(self, user_id: int, lead_ids: list[int]) -> int:
        """Hard-delete unsaved inbox leads by ID."""
        if not lead_ids:
            return 0
        count = (
            self.db.query(Lead)
            .filter(
                Lead.user_id == user_id,
                Lead.id.in_(lead_ids),
                or_(Lead.is_saved.is_(False), Lead.is_saved.is_(None)),
            )
            .delete(synchronize_session=False)
        )
        self.db.commit()
        return count

    def get_many_by_ids(self, user_id: int, lead_ids: list[int]) -> list[Lead]:
        if not lead_ids:
            return []
        return (
            self.db.query(Lead)
            .filter(Lead.user_id == user_id, Lead.id.in_(lead_ids))
            .all()
        )

    def delete_matching(
        self,
        user_id: int,
        q: str | None = None,
        city: str | None = None,
        country: str | None = None,
        industry: str | None = None,
        status: LeadStatus | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        source: str | None = None,
        quality_tier: str | None = None,
        whatsapp_ready: bool | None = None,
        has_email: bool | None = None,
        has_website: bool | None = None,
        saved: bool | None = None,
    ) -> int:
        count = self._filtered_query(
            user_id,
            q,
            city,
            country,
            industry,
            status,
            date_from,
            date_to,
            source,
            quality_tier,
            whatsapp_ready,
            has_email,
            has_website,
            saved,
        ).delete(synchronize_session=False)
        self.db.commit()
        return count

    def search(
        self,
        user_id: int,
        q: str | None = None,
        city: str | None = None,
        country: str | None = None,
        industry: str | None = None,
        status: LeadStatus | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        source: str | None = None,
        quality_tier: str | None = None,
        whatsapp_ready: bool | None = None,
        has_email: bool | None = None,
        has_website: bool | None = None,
        saved: bool | None = None,
        include_background: bool = False,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Lead], int]:
        query = self._filtered_query(
            user_id,
            q,
            city,
            country,
            industry,
            status,
            date_from,
            date_to,
            source,
            quality_tier,
            whatsapp_ready,
            has_email,
            has_website,
            saved,
            include_background=include_background,
        )

        total = query.count()
        order = Lead.saved_at.desc() if saved else Lead.created_at.desc()
        leads = (
            query.order_by(order)
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return leads, total

    def get_all_for_user(self, user_id: int, lead_ids: list[int] | None = None) -> list[Lead]:
        query = self.db.query(Lead).filter(
            Lead.user_id == user_id, self._exclude_background_filter()
        )
        if lead_ids:
            query = query.filter(Lead.id.in_(lead_ids))
        return query.order_by(Lead.created_at.desc()).all()

    def _dashboard_lead_filter(self):
        return self._exclude_background_filter()

    def count_by_status(self, user_id: int, status: LeadStatus) -> int:
        return (
            self.db.query(func.count(Lead.id))
            .filter(Lead.user_id == user_id, Lead.status == status)
            .scalar()
            or 0
        )

    def count_total(self, user_id: int) -> int:
        return (
            self.db.query(func.count(Lead.id)).filter(Lead.user_id == user_id).scalar() or 0
        )

    def count_dashboard_total(self, user_id: int) -> int:
        return (
            self.db.query(func.count(Lead.id))
            .filter(Lead.user_id == user_id, self._dashboard_lead_filter())
            .scalar()
            or 0
        )

    def count_dashboard_by_status(self, user_id: int, status: LeadStatus) -> int:
        return (
            self.db.query(func.count(Lead.id))
            .filter(
                Lead.user_id == user_id,
                Lead.status == status,
                self._dashboard_lead_filter(),
            )
            .scalar()
            or 0
        )

    def count_saved(self, user_id: int) -> int:
        return (
            self.db.query(func.count(Lead.id))
            .filter(Lead.user_id == user_id, Lead.is_saved.is_(True))
            .scalar()
            or 0
        )

    def count_inbox(self, user_id: int) -> int:
        return (
            self.db.query(func.count(Lead.id))
            .filter(
                Lead.user_id == user_id,
                or_(Lead.is_saved.is_(False), Lead.is_saved.is_(None)),
                self._exclude_background_filter(),
            )
            .scalar()
            or 0
        )

    def count_background_leads(self, user_id: int) -> int:
        flag = func.json_extract(Lead.intelligence_meta, "$.scrape_context.background")
        return (
            self.db.query(func.count(Lead.id))
            .filter(
                Lead.user_id == user_id,
                or_(flag == 1, flag == True, flag == "true"),  # noqa: E712
            )
            .scalar()
            or 0
        )

    def count_without_website(self, user_id: int) -> int:
        return (
            self.db.query(func.count(Lead.id))
            .filter(
                Lead.user_id == user_id,
                or_(Lead.website.is_(None), Lead.website == ""),
            )
            .scalar()
            or 0
        )

    def count_with_phone(self, user_id: int) -> int:
        return (
            self.db.query(func.count(Lead.id))
            .filter(Lead.user_id == user_id, Lead.phone.isnot(None), Lead.phone != "")
            .scalar()
            or 0
        )

    def list_recent_background_leads(self, user_id: int, limit: int = 10) -> list[Lead]:
        flag = func.json_extract(Lead.intelligence_meta, "$.scrape_context.background")
        return (
            self.db.query(Lead)
            .filter(
                Lead.user_id == user_id,
                or_(flag == 1, flag == True, flag == "true"),  # noqa: E712
            )
            .order_by(Lead.created_at.desc())
            .limit(limit)
            .all()
        )

    def list_for_campaign_run(
        self,
        user_id: int,
        status: LeadStatus | None = None,
        lead_ids: list[int] | None = None,
        limit: int = 100,
    ) -> list[Lead]:
        query = self.db.query(Lead).filter(Lead.user_id == user_id)
        if status:
            query = query.filter(Lead.status == status)
        if lead_ids:
            query = query.filter(Lead.id.in_(lead_ids))
        return query.order_by(Lead.created_at.desc()).limit(limit).all()

    def save_by_ids(self, user_id: int, lead_ids: list[int]) -> int:
        if not lead_ids:
            return 0
        now = datetime.now(UTC)
        count = (
            self._filtered_query(user_id, saved=False)
            .filter(Lead.id.in_(lead_ids))
            .update({"is_saved": True, "saved_at": now}, synchronize_session=False)
        )
        self.db.commit()
        return count

    def unsave(self, lead: Lead) -> Lead:
        lead.is_saved = False
        lead.saved_at = None
        self.db.commit()
        self.db.refresh(lead)
        return lead
