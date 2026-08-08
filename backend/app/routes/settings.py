from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.auth import get_current_admin, get_current_user
from app.core.config import get_settings
from app.database.database import get_db
from app.models.user import User, UserPlan
from app.schemas.common import LeadDatabaseStatsResponse
from app.schemas.payment import PaymentMethodResponse, PurchaseProPlanRequest
from app.schemas.user import (
    PlanOptionResponse,
    PlansCatalogResponse,
    PurchaseProPlanResponse,
    UsageQuotaResponse,
)
from app.services.lead_database_service import LeadDatabaseService
from app.services.plan_payment_service import PlanPaymentService
from app.services.jazzcash_service import jazzcash_configured
from app.services.token_quota_service import (
    DEFAULT_FREE_DAILY_TOKENS,
    DEFAULT_PAID_DAILY_TOKENS,
    ensure_token_day,
    usage_snapshot,
)

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get(
    "/database",
    response_model=LeadDatabaseStatsResponse,
    summary="Lead database stats (admin only)",
)
def get_lead_database_stats(
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> LeadDatabaseStatsResponse:
    return LeadDatabaseService(db).get_stats(current_user)


@router.get(
    "/usage",
    response_model=UsageQuotaResponse,
    summary="Current user's daily API token usage",
)
def get_usage_quota(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UsageQuotaResponse:
    user = ensure_token_day(current_user, db)
    return UsageQuotaResponse(**usage_snapshot(user))


@router.post(
    "/request-own-api-keys",
    response_model=UsageQuotaResponse,
    summary="Request permission to add your own API keys",
)
def request_own_api_keys(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UsageQuotaResponse:
    user = ensure_token_day(current_user, db)
    if user.own_api_keys_enabled:
        return UsageQuotaResponse(**usage_snapshot(user))
    user.own_api_keys_requested = True
    db.commit()
    db.refresh(user)
    return UsageQuotaResponse(**usage_snapshot(user))


@router.post(
    "/request-paid-plan",
    response_model=UsageQuotaResponse,
    summary="Request upgrade to the paid plan",
)
def request_paid_plan(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UsageQuotaResponse:
    user = ensure_token_day(current_user, db)
    plan_value = user.plan.value if hasattr(user.plan, "value") else str(user.plan)
    if plan_value == "paid":
        return UsageQuotaResponse(**usage_snapshot(user))
    user.paid_plan_requested = True
    db.commit()
    db.refresh(user)
    return UsageQuotaResponse(**usage_snapshot(user))


@router.get(
    "/plans",
    response_model=PlansCatalogResponse,
    summary="Available subscription plans",
)
def get_plans_catalog(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PlansCatalogResponse:
    settings = get_settings()
    user = ensure_token_day(current_user, db)
    plan_value = user.plan.value if hasattr(user.plan, "value") else str(user.plan)
    checkout = settings.PRO_PLAN_CHECKOUT_URL.strip() or None
    contact = (
        settings.PRO_PLAN_CONTACT_EMAIL.strip()
        or settings.ADMIN_EMAIL.strip()
        or None
    )
    return PlansCatalogResponse(
        current_plan=plan_value,
        paid_plan_requested=bool(user.paid_plan_requested),
        checkout_url=checkout,
        contact_email=contact,
        price_pkr=settings.PRO_PLAN_PRICE_PKR if jazzcash_configured(settings) else None,
        payment_methods=[
            PaymentMethodResponse(**m) for m in PlanPaymentService.payment_methods(settings)
        ],
        plans=[
            PlanOptionResponse(
                id="free",
                name="Free",
                price_usd=0,
                daily_tokens=DEFAULT_FREE_DAILY_TOKENS,
                features=[
                    f"{DEFAULT_FREE_DAILY_TOKENS} platform API tokens per day",
                    "Lead scraping & AI outreach",
                    "Email account connection",
                ],
                is_current=plan_value == UserPlan.free.value,
            ),
            PlanOptionResponse(
                id="pro",
                name="Pro",
                price_usd=settings.PRO_PLAN_PRICE_USD,
                daily_tokens=DEFAULT_PAID_DAILY_TOKENS,
                features=[
                    f"{DEFAULT_PAID_DAILY_TOKENS} platform API tokens per day",
                    "Priority platform API access",
                    "Request own Apify & Groq keys",
                    "Higher daily scraping & AI limits",
                ],
                is_current=plan_value == UserPlan.paid.value,
            ),
        ],
    )


@router.post(
    "/purchase-pro-plan",
    response_model=PurchaseProPlanResponse,
    summary="Purchase or request Pro plan upgrade",
)
def purchase_pro_plan(
    data: PurchaseProPlanRequest = PurchaseProPlanRequest(),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PurchaseProPlanResponse:
    settings = get_settings()
    user = ensure_token_day(current_user, db)
    plan_value = user.plan.value if hasattr(user.plan, "value") else str(user.plan)
    payment_method = data.payment_method or "jazzcash"

    if plan_value == UserPlan.paid.value:
        return PurchaseProPlanResponse(
            action="already_active",
            message="You are already on the Pro plan.",
            usage=UsageQuotaResponse(**usage_snapshot(user)),
        )

    if payment_method == "jazzcash" and jazzcash_configured(settings):
        jc = PlanPaymentService(db).initiate_jazzcash(user)
        return PurchaseProPlanResponse(
            action="jazzcash_form",
            post_url=jc["post_url"],
            fields=jc["fields"],
            txn_ref_no=jc["txn_ref_no"],
            amount_pkr=jc["amount_pkr"],
            message=jc["message"],
            usage=UsageQuotaResponse(**usage_snapshot(user)),
        )

    checkout = settings.PRO_PLAN_CHECKOUT_URL.strip()
    if checkout:
        user.paid_plan_requested = True
        db.commit()
        db.refresh(user)
        return PurchaseProPlanResponse(
            action="redirect",
            checkout_url=checkout,
            message="Redirecting to secure checkout…",
            usage=UsageQuotaResponse(**usage_snapshot(user)),
        )

    user.paid_plan_requested = True
    db.commit()
    db.refresh(user)
    contact = settings.PRO_PLAN_CONTACT_EMAIL.strip() or settings.ADMIN_EMAIL.strip()
    if contact:
        message = (
            f"Pro plan purchase request sent. Admin ({contact}) will activate your account shortly."
        )
    else:
        message = "Pro plan purchase request sent. An admin will activate your account shortly."
    return PurchaseProPlanResponse(
        action="request",
        message=message,
        usage=UsageQuotaResponse(**usage_snapshot(user)),
    )
