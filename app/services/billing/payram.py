"""PayRam payment-provider adapter.

Implements :class:`app.services.billing.provider.PaymentProvider` against the
documented PayRam Payments API (https://docs.payram.com/api-integration/payments-api):

- ``POST {BASE_URL}/api/v1/payment``                      create a payment link
- ``GET  {BASE_URL}/api/v1/payment/reference/{ref}``      read current status
- Webhook ``X-Payram-Signature: sha256=<hex>`` = HMAC-SHA256(raw body, API key)

Only server-side ``requests`` calls — no Node.js SDK is pulled into this Python
app. Provider statuses (OPEN / PARTIALLY_FILLED / FILLED / OVER_FILLED /
CANCELLED) are normalized into :class:`PaymentStatus`.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
from typing import Mapping

import requests

from app.services.billing.provider import (
    CheckoutSession,
    PaymentProvider,
    PaymentSnapshot,
    PaymentStatus,
    ProviderError,
    WebhookEvent,
    is_trusted_checkout_url,
    to_float,
)

logger = logging.getLogger(__name__)

# PayRam fill-state -> normalized status.
_STATUS_MAP: dict[str, PaymentStatus] = {
    "OPEN": PaymentStatus.AWAITING,
    "PARTIALLY_FILLED": PaymentStatus.PARTIALLY_PAID,
    "FILLED": PaymentStatus.PAID,
    "OVER_FILLED": PaymentStatus.OVERPAID,
    "CANCELLED": PaymentStatus.CANCELLED,
}


def map_status(raw: str | None) -> PaymentStatus:
    return _STATUS_MAP.get(str(raw or "").strip().upper(), PaymentStatus.UNKNOWN)


def _first(data: dict, *keys):
    """Return the first present, non-empty value among ``keys``.

    PayRam's webhook uses snake_case while the status API uses camelCase, so the
    adapter tolerates both.
    """
    for key in keys:
        value = data.get(key)
        if value is not None and value != "":
            return value
    return None


def snapshot_from_dict(data: dict, fallback_reference: str = "") -> PaymentSnapshot:
    """Normalize a PayRam payment payload (status API or webhook) — pure."""
    raw_status = str(_first(data, "paymentState", "status") or "")
    return PaymentSnapshot(
        reference_id=str(_first(data, "referenceID", "reference_id") or fallback_reference),
        status=map_status(raw_status),
        raw_status=raw_status,
        invoice_ref=str(_first(data, "invoiceID", "invoice_id") or ""),
        customer_id=str(_first(data, "customerID", "customer_id") or ""),
        amount_usd=to_float(_first(data, "amountInUSD", "amount_in_usd", "amount")),
        paid_amount_usd=to_float(
            _first(data, "filledAmountInUSD", "filled_amount_in_usd", "filledAmount")
        ),
        currency=str(_first(data, "currency", "currencyCode", "currencySymbol") or ""),
    )


class PayRamProvider(PaymentProvider):
    name = "payram"

    def __init__(self, base_url: str, api_key: str, webhook_secret: str, timeout: float = 15.0):
        if not base_url or not api_key:
            raise ProviderError("PayRam base URL and API key are required")
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        # PayRam signs with the project API key unless an override is configured.
        self.webhook_secret = webhook_secret or api_key
        self.timeout = timeout

    # -- internal ---------------------------------------------------------

    def _headers(self) -> dict[str, str]:
        return {"API-Key": self.api_key, "Content-Type": "application/json"}

    # -- provider contract ------------------------------------------------

    def create_checkout(
        self,
        *,
        invoice_ref: str,
        customer_email: str,
        customer_id: str,
        amount_usd: float,
        expires_at: str | None = None,
        currency: str | None = None,
        network: str | None = None,
    ) -> CheckoutSession:
        body: dict = {
            "customerEmail": customer_email,
            "customerID": str(customer_id),
            "amountInUSD": round(float(amount_usd), 2),
            "invoiceID": invoice_ref,
        }
        if expires_at:
            body["expire"] = expires_at
        if currency:
            body["currency"] = currency
        if network:
            body["network"] = network

        try:
            response = requests.post(
                f"{self.base_url}/api/v1/payment",
                headers=self._headers(),
                json=body,
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            # Creation is not safely retryable (no idempotency key in the API):
            # surface the failure and let the invoice stay pending for reconcile.
            raise ProviderError(f"PayRam create payment request failed: {exc}") from exc

        if response.status_code >= 400:
            logger.warning("payram.create_failed", extra={"status": response.status_code})
            raise ProviderError(f"PayRam create payment returned {response.status_code}")

        try:
            data = response.json()
        except ValueError as exc:
            raise ProviderError("PayRam create payment returned non-JSON") from exc

        reference_id = str(data.get("reference_id") or "").strip()
        checkout_url = str(data.get("url") or "").strip()
        if not reference_id or not checkout_url:
            raise ProviderError("PayRam create payment response missing reference_id/url")
        if not is_trusted_checkout_url(checkout_url, self.base_url):
            # Never redirect the browser to an untrusted host.
            raise ProviderError("PayRam returned a checkout URL outside its own host")

        return CheckoutSession(
            reference_id=reference_id,
            checkout_url=checkout_url,
            host=str(data.get("host") or "").strip(),
        )

    def get_payment(self, reference_id: str) -> PaymentSnapshot:
        if not reference_id:
            raise ProviderError("reference_id is required")
        try:
            response = requests.get(
                f"{self.base_url}/api/v1/payment/reference/{reference_id}",
                headers=self._headers(),
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            raise ProviderError(f"PayRam payment lookup failed: {exc}") from exc

        if response.status_code == 404:
            raise ProviderError("PayRam payment not found")
        if response.status_code >= 400:
            raise ProviderError(f"PayRam payment lookup returned {response.status_code}")

        try:
            data = response.json()
        except ValueError as exc:
            raise ProviderError("PayRam payment lookup returned non-JSON") from exc

        if not isinstance(data, dict):
            raise ProviderError("PayRam payment lookup returned unexpected payload")
        return snapshot_from_dict(data, fallback_reference=reference_id)

    def verify_webhook(self, raw_body: bytes, headers: Mapping[str, str]) -> bool:
        """Verify authenticity via HMAC-SHA256 signature (constant-time).

        Preferred header is ``X-Payram-Signature`` (``sha256=<hex>``). The
        legacy verbatim ``API-KEY`` header is accepted for backward
        compatibility, also compared in constant time.
        """
        lowered = {k.lower(): v for k, v in headers.items()}

        signature = lowered.get("x-payram-signature", "")
        if signature:
            expected = (
                "sha256="
                + hmac.new(
                    self.webhook_secret.encode("utf-8"), raw_body, hashlib.sha256
                ).hexdigest()
            )
            return hmac.compare_digest(signature.strip(), expected)

        legacy = lowered.get("api-key", "")
        if legacy:
            return hmac.compare_digest(legacy, self.api_key)

        return False

    def parse_webhook(self, raw_body: bytes, headers: Mapping[str, str]) -> WebhookEvent:
        try:
            data = json.loads(raw_body.decode("utf-8"))
        except (ValueError, UnicodeDecodeError) as exc:
            raise ProviderError("PayRam webhook body is not valid JSON") from exc
        if not isinstance(data, dict):
            raise ProviderError("PayRam webhook body is not a JSON object")

        reference_id = str(_first(data, "reference_id", "referenceID") or "").strip()
        raw_status = str(_first(data, "status", "paymentState") or "").strip().upper()
        if not reference_id or not raw_status:
            raise ProviderError("PayRam webhook missing reference_id/status")

        status = map_status(raw_status)
        # Idempotency key: provider + reference + status. The same confirmed
        # payment can never be fulfilled twice (unique index enforces this).
        dedup_key = f"{self.name}:{reference_id}:{raw_status}"

        return WebhookEvent(
            provider=self.name,
            reference_id=reference_id,
            invoice_ref=str(_first(data, "invoice_id", "invoiceID") or "").strip(),
            status=status,
            raw_status=raw_status,
            dedup_key=dedup_key,
            event_type="payment",
            amount_usd=to_float(_first(data, "amount", "amountInUSD")),
            paid_amount_usd=to_float(_first(data, "filled_amount_in_usd", "filledAmountInUSD")),
            currency=str(_first(data, "currency", "currencyCode") or ""),
            customer_id=str(_first(data, "customer_id", "customerID") or ""),
            timestamp=data.get("timestamp") if isinstance(data.get("timestamp"), int) else None,
        )
