from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.config import get_settings
from app.database.database import get_db
from app.models.user import User
from app.schemas.payment import JazzCashInitiateResponse, PaymentMethodResponse
from app.services.plan_payment_service import PlanPaymentService

router = APIRouter(prefix="/api/payments", tags=["payments"])


@router.get(
    "/methods",
    response_model=list[PaymentMethodResponse],
    summary="Available payment methods for Pro plan",
)
def list_payment_methods(
    current_user: User = Depends(get_current_user),
) -> list[PaymentMethodResponse]:
    _ = current_user
    methods = PlanPaymentService.payment_methods()
    return [PaymentMethodResponse(**m) for m in methods]


@router.post(
    "/jazzcash/initiate",
    response_model=JazzCashInitiateResponse,
    summary="Start JazzCash checkout for Pro plan",
)
def initiate_jazzcash(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JazzCashInitiateResponse:
    result = PlanPaymentService(db).initiate_jazzcash(current_user)
    return JazzCashInitiateResponse(**result)


@router.post("/jazzcash/return", include_in_schema=False)
async def jazzcash_return(request: Request, db: Session = Depends(get_db)):
    """JazzCash POST callback — verifies payment and redirects user to frontend."""
    form = await request.form()
    form_data = dict(form)
    status_val, txn_ref, message = PlanPaymentService(db).handle_jazzcash_return(form_data)

    settings = get_settings()
    frontend = settings.FRONTEND_URL.rstrip("/")
    from urllib.parse import quote

    redirect_url = (
        f"{frontend}/settings/plans/payment-result"
        f"?status={status_val}&ref={quote(txn_ref)}&msg={quote(message[:200])}"
    )
    return RedirectResponse(url=redirect_url, status_code=303)
