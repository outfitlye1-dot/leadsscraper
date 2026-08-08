from pydantic import BaseModel, Field


class PaymentMethodResponse(BaseModel):
    id: str
    name: str
    description: str
    currency: str
    amount: float


class JazzCashInitiateResponse(BaseModel):
    action: str = "jazzcash_form"
    post_url: str
    fields: dict[str, str]
    txn_ref_no: str
    amount_pkr: float
    message: str


class PurchaseProPlanRequest(BaseModel):
    payment_method: str = Field(default="jazzcash", description="jazzcash | request")
