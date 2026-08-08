from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import get_password_hash
from app.models.campaign import Campaign
from app.models.email_outreach import (
    EmailAccount,
    EmailAccountStatus,
    EmailOutreachCampaign,
    EmailOutreachSettings,
    OutreachEmail,
    OutreachEmailStatus,
    OutreachJob,
    OutreachJobStatus,
)
from app.models.lead import Lead
from app.models.message import Message
from app.models.user import User, UserPlan, UserRole
from app.models.user_api_key import UserApiKey
from app.repositories.user_repository import UserRepository
from app.schemas.admin import (
    AdminDashboardResponse,
    AdminLeadListItem,
    AdminLeadListResponse,
    AdminOutreachSummaryResponse,
    AdminScraperJobListResponse,
    AdminScraperJobResponse,
    AdminSystemResponse,
    AdminUserCreateRequest,
    AdminUserDetailResponse,
    AdminUserListItem,
    AdminUserListResponse,
    AdminUserStatsResponse,
    AdminUserUpdateRequest,
)
from app.schemas.user import UserResponse
from app.schemas.user_serialize import to_user_response
from app.services.scraper_job_store import scraper_job_store
from app.services.email_outreach.worker import outreach_worker
from app.services.token_quota_service import (
    default_limit_for_plan,
    ensure_token_day,
)

def _database_size_mb(database_url: str) -> float | None:
    if "sqlite" not in database_url.lower():
        return None
    raw = database_url.split("///", 1)[-1]
    path = Path(raw)
    if not path.is_absolute():
        path = Path.cwd() / path
    if not path.exists():
        return None
    return round(path.stat().st_size / (1024 * 1024), 2)


class AdminService:
    def __init__(self, db: Session):
        self.db = db
        self.users = UserRepository(db)

    def get_dashboard(self) -> AdminDashboardResponse:
        role_counts = self.users.count_by_role()
        active_jobs = sum(
            1
            for job in scraper_job_store.list_all(limit=500)
            if job.status in ("pending", "running", "paused")
        )
        settings = get_settings()
        return AdminDashboardResponse(
            total_users=self.db.query(func.count(User.id)).scalar() or 0,
            admin_users=role_counts.get(UserRole.admin.value, 0),
            regular_users=role_counts.get(UserRole.user.value, 0),
            total_leads=self.db.query(func.count(Lead.id)).scalar() or 0,
            total_campaigns=self.db.query(func.count(Campaign.id)).scalar() or 0,
            total_messages=self.db.query(func.count(Message.id)).scalar() or 0,
            total_api_keys=self.db.query(func.count(UserApiKey.id)).scalar() or 0,
            total_outreach_emails=self.db.query(func.count(OutreachEmail.id)).scalar() or 0,
            total_outreach_campaigns=self.db.query(func.count(EmailOutreachCampaign.id)).scalar() or 0,
            active_scraper_jobs=active_jobs,
            outreach_worker_enabled=settings.OUTREACH_WORKER_ENABLED,
        )

    def list_users(
        self,
        *,
        search: str | None = None,
        role: UserRole | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> AdminUserListResponse:
        offset = max(page - 1, 0) * page_size
        users, total = self.users.list_users(
            search=search, role=role, offset=offset, limit=page_size
        )
        items: list[AdminUserListItem] = []
        for user in users:
            ensure_token_day(user, self.db)
            stats = self._user_stats(user.id)
            item = AdminUserListItem.model_validate(to_user_response(user, self.db).model_dump())
            item.lead_count = stats.leads
            item.campaign_count = stats.campaigns
            items.append(item)
        return AdminUserListResponse(
            items=items, total=total, page=page, page_size=page_size
        )

    def get_user(self, user_id: int) -> AdminUserDetailResponse:
        user = self.users.get_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        ensure_token_day(user, self.db)
        return AdminUserDetailResponse(
            **to_user_response(user, self.db).model_dump(),
            stats=self._user_stats(user.id),
        )

    def create_user(self, data: AdminUserCreateRequest) -> UserResponse:
        if self.users.get_by_email(data.email):
            raise HTTPException(status_code=400, detail="Email already registered")
        user = self.users.create(
            name=data.name,
            email=data.email,
            password_hash=get_password_hash(data.password),
            role=data.role,
        )
        patch: dict = {}
        if data.plan is not None:
            patch["plan"] = data.plan
            if data.daily_token_limit is None:
                patch["daily_token_limit"] = default_limit_for_plan(data.plan)
        if data.daily_token_limit is not None:
            patch["daily_token_limit"] = data.daily_token_limit
        if patch:
            user = self.users.update_user(user, patch)
        return to_user_response(user, self.db)

    def update_user(
        self, actor: User, user_id: int, data: AdminUserUpdateRequest
    ) -> UserResponse:
        user = self.users.get_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        patch: dict = {}
        if data.name is not None:
            patch["name"] = data.name
        if data.email is not None:
            email = data.email.lower()
            existing = self.users.get_by_email(email)
            if existing and existing.id != user.id:
                raise HTTPException(status_code=400, detail="Email already in use")
            patch["email"] = email
        if data.role is not None:
            if user.id == actor.id and data.role != UserRole.admin:
                raise HTTPException(
                    status_code=400, detail="You cannot remove your own admin role"
                )
            patch["role"] = data.role
        if data.api_access is not None:
            patch["api_access"] = data.api_access
        if data.plan is not None:
            patch["plan"] = data.plan
            if data.daily_token_limit is None:
                patch["daily_token_limit"] = default_limit_for_plan(data.plan)
            plan_val = data.plan.value if hasattr(data.plan, "value") else str(data.plan)
            if plan_val == UserPlan.paid.value:
                patch["paid_plan_requested"] = False
        if data.daily_token_limit is not None:
            patch["daily_token_limit"] = data.daily_token_limit
        if data.own_api_keys_enabled is not None:
            patch["own_api_keys_enabled"] = data.own_api_keys_enabled
            if data.own_api_keys_enabled:
                patch["own_api_keys_requested"] = False
        if data.reset_tokens_used_today:
            patch["tokens_used_today"] = 0
            from app.services.token_quota_service import utc_today

            patch["tokens_reset_on"] = utc_today()
        if patch:
            self.users.update_user(user, patch)
        if data.password:
            self.users.update_password(user, get_password_hash(data.password))
        return to_user_response(user, self.db)

    def delete_user(self, actor: User, user_id: int) -> None:
        if actor.id == user_id:
            raise HTTPException(status_code=400, detail="You cannot delete your own account")
        user = self.users.get_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        self.users.delete_user(user)

    def list_leads(
        self,
        *,
        search: str | None = None,
        user_id: int | None = None,
        page: int = 1,
        page_size: int = 25,
    ) -> AdminLeadListResponse:
        query = self.db.query(Lead, User.email).join(User, User.id == Lead.user_id)
        if user_id is not None:
            query = query.filter(Lead.user_id == user_id)
        if search:
            term = f"%{search.strip()}%"
            query = query.filter(
                (Lead.company_name.ilike(term))
                | (Lead.email.ilike(term))
                | (Lead.city.ilike(term))
                | (User.email.ilike(term))
            )
        total = query.count()
        rows = (
            query.order_by(Lead.created_at.desc())
            .offset(max(page - 1, 0) * page_size)
            .limit(page_size)
            .all()
        )
        items = [
            AdminLeadListItem(
                id=lead.id,
                user_id=lead.user_id,
                user_email=user_email,
                company_name=lead.company_name,
                email=lead.email,
                phone=lead.phone,
                city=lead.city,
                country=lead.country,
                status=lead.status.value if hasattr(lead.status, "value") else str(lead.status),
                is_saved=lead.is_saved,
                created_at=lead.created_at,
            )
            for lead, user_email in rows
        ]
        return AdminLeadListResponse(
            items=items, total=total, page=page, page_size=page_size
        )

    def delete_lead(self, lead_id: int) -> None:
        lead = self.db.query(Lead).filter(Lead.id == lead_id).first()
        if not lead:
            raise HTTPException(status_code=404, detail="Lead not found")
        self.db.delete(lead)
        self.db.commit()

    def list_scraper_jobs(self) -> AdminScraperJobListResponse:
        user_emails = {
            u.id: u.email for u in self.db.query(User.id, User.email).all()
        }
        items = [
            AdminScraperJobResponse(
                job_id=job.job_id,
                user_id=job.user_id,
                user_email=user_emails.get(job.user_id),
                status=job.status,
                mode=job.mode,
                progress=job.progress,
                stage=job.stage,
                message=job.message,
                created_at=job.created_at,
                updated_at=job.updated_at,
            )
            for job in scraper_job_store.list_all(limit=100)
        ]
        return AdminScraperJobListResponse(items=items)

    def cancel_scraper_job(self, job_id: str) -> None:
        if not scraper_job_store.admin_cancel(job_id):
            raise HTTPException(status_code=404, detail="Job not found or not cancellable")

    def outreach_summary(self) -> AdminOutreachSummaryResponse:
        return AdminOutreachSummaryResponse(
            total_accounts=self.db.query(func.count(EmailAccount.id)).scalar() or 0,
            connected_accounts=self.db.query(func.count(EmailAccount.id))
            .filter(EmailAccount.status == EmailAccountStatus.connected)
            .scalar()
            or 0,
            agents_running=self.db.query(func.count(EmailOutreachSettings.id))
            .filter(EmailOutreachSettings.agent_running.is_(True))
            .scalar()
            or 0,
            emails_sent=self.db.query(func.count(OutreachEmail.id))
            .filter(OutreachEmail.status.in_([OutreachEmailStatus.sent, OutreachEmailStatus.delivered, OutreachEmailStatus.opened, OutreachEmailStatus.replied]))
            .scalar()
            or 0,
            emails_queued=self.db.query(func.count(OutreachEmail.id))
            .filter(OutreachEmail.status == OutreachEmailStatus.queued)
            .scalar()
            or 0,
            replies_received=self.db.query(func.count(OutreachEmail.id))
            .filter(OutreachEmail.status == OutreachEmailStatus.replied)
            .scalar()
            or 0,
            pending_jobs=self.db.query(func.count(OutreachJob.id))
            .filter(OutreachJob.status == OutreachJobStatus.pending)
            .scalar()
            or 0,
        )

    def get_system(self) -> AdminSystemResponse:
        settings = get_settings()
        db_url = settings.DATABASE_URL
        if "@" in db_url:
            db_url = db_url.split("@", 1)[-1]
        db_type = "sqlite" if "sqlite" in settings.DATABASE_URL.lower() else "other"
        active_jobs = sum(
            1
            for job in scraper_job_store.list_all(limit=500)
            if job.status in ("pending", "running", "paused")
        )
        worker_thread = outreach_worker._thread
        worker_running = bool(worker_thread and worker_thread.is_alive())
        return AdminSystemResponse(
            status="healthy",
            app_name=settings.APP_NAME,
            app_version=settings.APP_VERSION,
            database_url=db_url,
            database_type=db_type,
            database_size_mb=_database_size_mb(settings.DATABASE_URL),
            outreach_worker_enabled=settings.OUTREACH_WORKER_ENABLED,
            outreach_worker_running=worker_running,
            outreach_worker_poll_seconds=settings.OUTREACH_WORKER_POLL_SECONDS,
            outreach_sync_interval_seconds=settings.OUTREACH_SYNC_INTERVAL_SECONDS,
            smtp_configured=settings.smtp_configured,
            google_oauth_configured=bool(settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET),
            microsoft_oauth_configured=bool(
                settings.MICROSOFT_CLIENT_ID and settings.MICROSOFT_CLIENT_SECRET
            ),
            scraper_workers=settings.SCRAPER_WORKERS,
            scraper_fast_mode=settings.SCRAPER_FAST_MODE,
            scraper_playwright_enabled=settings.SCRAPER_ENABLE_PLAYWRIGHT,
            scraper_timeout=settings.SCRAPER_TIMEOUT,
            groq_model=settings.GROQ_MODEL,
            otp_dev_mode=settings.effective_otp_dev_mode,
            frontend_url=settings.FRONTEND_URL,
            default_secret_key=settings.SECRET_KEY
            == "change-me-in-production-use-a-long-random-string",
            upload_dir=settings.UPLOAD_DIR,
            export_dir=settings.EXPORT_DIR,
            total_users=self.db.query(func.count(User.id)).scalar() or 0,
            total_leads=self.db.query(func.count(Lead.id)).scalar() or 0,
            total_messages=self.db.query(func.count(Message.id)).scalar() or 0,
            total_api_keys=self.db.query(func.count(UserApiKey.id)).scalar() or 0,
            active_scraper_jobs=active_jobs,
            outreach_agents_running=self.db.query(func.count(EmailOutreachSettings.id))
            .filter(EmailOutreachSettings.agent_running.is_(True))
            .scalar()
            or 0,
            outreach_pending_jobs=self.db.query(func.count(OutreachJob.id))
            .filter(OutreachJob.status == OutreachJobStatus.pending)
            .scalar()
            or 0,
            checked_at=datetime.now(UTC),
        )

    def _user_stats(self, user_id: int) -> AdminUserStatsResponse:
        return AdminUserStatsResponse(
            leads=self.db.query(func.count(Lead.id)).filter(Lead.user_id == user_id).scalar() or 0,
            campaigns=self.db.query(func.count(Campaign.id)).filter(Campaign.user_id == user_id).scalar() or 0,
            messages=self.db.query(func.count(Message.id)).filter(Message.user_id == user_id).scalar() or 0,
            api_keys=self.db.query(func.count(UserApiKey.id)).filter(UserApiKey.user_id == user_id).scalar() or 0,
            outreach_emails=self.db.query(func.count(OutreachEmail.id)).filter(OutreachEmail.user_id == user_id).scalar() or 0,
            email_accounts=self.db.query(func.count(EmailAccount.id)).filter(EmailAccount.user_id == user_id).scalar() or 0,
        )
