"""JazzCash hosted checkout (MWALLET) helpers."""

from __future__ import annotations

import hashlib
import hmac
import json
from datetime import UTC, datetime, timedelta

from app.core.config import Settings


def _txn_datetime(dt: datetime | None = None) -> str:
    return (dt or datetime.now(UTC)).strftime("%Y%m%d%H%M%S")


def _amount_paisa(price_pkr: float) -> str:
    """JazzCash expects amount without decimal point (100.00 PKR → 10000)."""
    return str(int(round(price_pkr * 100)))


def generate_secure_hash(data: dict[str, str], integrity_salt: str) -> str:
    """HMAC-SHA256 hash per JazzCash Payment Portal v2.0."""
    sorted_keys = sorted(k for k in data if k != "pp_SecureHash")
    parts = [integrity_salt]
    for key in sorted_keys:
        val = data.get(key, "")
        parts.append("" if val is None else str(val))
    hash_string = "&".join(parts)
    digest = hmac.new(
        integrity_salt.encode("utf-8"),
        hash_string.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return digest.upper()


def verify_secure_hash(data: dict[str, str], integrity_salt: str) -> bool:
    received = (data.get("pp_SecureHash") or "").upper()
    if not received:
        return False
    payload = {k: str(v) if v is not None else "" for k, v in data.items()}
    expected = generate_secure_hash(payload, integrity_salt)
    return hmac.compare_digest(received, expected)


def build_checkout_payload(
    settings: Settings,
    *,
    txn_ref_no: str,
    amount_pkr: float,
    bill_reference: str,
    description: str,
    return_url: str,
    customer_email: str = "",
    customer_mobile: str = "",
    user_id: int | None = None,
) -> dict[str, str]:
    now = datetime.now(UTC)
    expiry = now + timedelta(days=1)
    payload: dict[str, str] = {
        "pp_Version": settings.JAZZCASH_VERSION,
        "pp_TxnType": settings.JAZZCASH_TXN_TYPE,
        "pp_Language": "EN",
        "pp_MerchantID": settings.JAZZCASH_MERCHANT_ID.strip(),
        "pp_SubMerchantID": "",
        "pp_Password": settings.JAZZCASH_PASSWORD.strip(),
        "pp_BankID": "",
        "pp_ProductID": "",
        "pp_TxnRefNo": txn_ref_no,
        "pp_Amount": _amount_paisa(amount_pkr),
        "pp_TxnCurrency": "PKR",
        "pp_TxnDateTime": _txn_datetime(now),
        "pp_TxnExpiryDateTime": _txn_datetime(expiry),
        "pp_BillReference": bill_reference[:20],
        "pp_Description": description[:200],
        "pp_ReturnURL": return_url,
        "ppmpf_1": str(user_id or ""),
        "ppmpf_2": "",
        "ppmpf_3": "",
        "ppmpf_4": "",
        "ppmpf_5": "",
        "pp_SecureHash": "",
    }
    payload["pp_SecureHash"] = generate_secure_hash(
        payload, settings.JAZZCASH_INTEGRITY_SALT.strip()
    )
    return payload


def jazzcash_configured(settings: Settings) -> bool:
    return bool(
        settings.JAZZCASH_MERCHANT_ID.strip()
        and settings.JAZZCASH_PASSWORD.strip()
        and settings.JAZZCASH_INTEGRITY_SALT.strip()
    )


def jazzcash_post_url(settings: Settings) -> str:
    if settings.JAZZCASH_SANDBOX:
        return (
            "https://sandbox.jazzcash.com.pk/CustomerPortal/"
            "transactionmanagement/merchantform/"
        )
    return (
        "https://payments.jazzcash.com.pk/CustomerPortal/"
        "transactionmanagement/merchantform/"
    )


def response_to_json(data: dict) -> str:
    return json.dumps({k: str(v) if v is not None else "" for k, v in data.items()})
