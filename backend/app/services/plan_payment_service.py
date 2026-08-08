from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.models.plan_payment import PaymentStatus, PlanPayment
from app.models.user import User, UserPlan
from app.repositories.user_repository import UserRepository
from app.services.jazzcash_service import (
    build_checkout_payload,
    jazzcash_configured,
    jazzcash_post_url,
    response_to_json,
    verify_secure_hash,
)
from app.services.token_quota_service import DEFAULT_PAID_DAILY_TOKENS, default_limit_for_plan


class PlanPaymentService:
    def __init__(self, db: Session):
        self.db = db
        self.users = UserRepository(db)
        self.settings = get_settings()

    def _new_txn_ref(self, user_id: int) -> str:
        stamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
        suffix = uuid.uuid4().hex[:6].upper()
        return f"LG{user_id}{stamp}{suffix}"[:20]

    def initiate_jazzcash(self, user: User) -> dict:
        settings = self.settings
        if not jazzcash_configured(settings):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=(
                    "JazzCash is not configured. Ask admin to add merchant credentials in .env"
                ),
            )

        plan_value = user.plan.value if hasattr(user.plan, "value") else str(user.plan)
        if plan_value == UserPlan.paid.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You are already on the Pro plan.",
            )

        amount_pkr = settings.PRO_PLAN_PRICE_PKR
        txn_ref = self._new_txn_ref(user.id)
        amount_paisa = int(round(amount_pkr * 100))

        payment = PlanPayment(
            user_id=user.id,
            txn_ref_no=txn_ref,
            amount_paisa=amount_paisa,
            plan="pro",
            provider="jazzcash",
            status=PaymentStatus.pending.value,
        )
        self.db.add(payment)
        self.db.commit()

        backend_base = settings.BACKEND_PUBLIC_URL.rstrip("/")
        return_url = f"{backend_base}/api/payments/jazzcash/return"
        fields = build_checkout_payload(
            settings,
            txn_ref_no=txn_ref,
            amount_pkr=amount_pkr,
            bill_reference=f"PRO-{user.id}",
            description=f"LeadGen Pro plan — {user.email}",
            return_url=return_url,
            customer_email=user.email,
            user_id=user.id,
        )

        return {
            "action": "jazzcash_form",
            "post_url": jazzcash_post_url(settings),
            "fields": fields,
            "txn_ref_no": txn_ref,
            "amount_pkr": amount_pkr,
            "message": "Redirecting to JazzCash…",
        }

    def handle_jazzcash_return(self, form_data: dict) -> tuple[str, str, str]:
        """Process JazzCash POST callback. Returns (status, txn_ref, message)."""
        settings = self.settings
        data = {k: str(v) if v is not None else "" for k, v in form_data.items()}

        if not verify_secure_hash(data, settings.JAZZCASH_INTEGRITY_SALT.strip()):
            return "failed", data.get("pp_TxnRefNo", ""), "Payment verification failed."

        txn_ref = data.get("pp_TxnRefNo", "")
        response_code = data.get("pp_ResponseCode", "")
        response_message = data.get("pp_ResponseMessage", "") or data.get("pp_ResponseMsg", "")

        payment = (
            self.db.query(PlanPayment).filter(PlanPayment.txn_ref_no == txn_ref).first()
        )
        if not payment:
            return "failed", txn_ref, "Payment record not found."

        payment.raw_response = response_to_json(data)
        payment.response_code = response_code
        payment.response_message = response_message[:512] if response_message else None

        if response_code == "000":
            payment.status = PaymentStatus.completed.value
            user = self.users.get_by_id(payment.user_id)
            if user:
                self.users.update_user(
                    user,
                    {
                        "plan": UserPlan.paid,
                        "daily_token_limit": default_limit_for_plan(UserPlan.paid),
                        "paid_plan_requested": False,
                        "tokens_used_today": 0,
                        "tokens_reset_on": datetime.now(UTC).date(),
                    },
                )
            self.db.commit()
            return "success", txn_ref, "Pro plan activated successfully."

        payment.status = PaymentStatus.failed.value
        self.db.commit()
        msg = response_message or "Payment was not completed."
        return "failed", txn_ref, msg

    @staticmethod
    def payment_methods(settings: Settings | None = None) -> list[dict]:
        settings = settings or get_settings()
        methods: list[dict] = []
        if jazzcash_configured(settings):
            methods.append(
                {
                    "id": "jazzcash",
                    "name": "JazzCash",
                    "description": "Pay with JazzCash mobile wallet",
                    "currency": "PKR",
                    "amount": settings.PRO_PLAN_PRICE_PKR,
                }
            )
        return methods
