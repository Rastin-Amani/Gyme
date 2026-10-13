"""Payment-provider abstraction.

Billing business logic (invoices, ledger, seats, enforcement) depends only on
this module. ``payram.py`` implements :class:`PaymentProvider`; a future Stripe
or Lemon Squeezy adapter can implement the same contract without touching
accounting, entitlements, or the UI.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Mapping, Protocol
from urllib.parse import urlparse


class PaymentStatus(str, Enum):
    """Provider-agnostic payment states (normalized from provider statuses)."""

    AWAITING = "awaiting"  # created, nothing deposited yet
    PARTIALLY_PAID = "partially_paid"
    PAID = "paid"
    OVERPAID = "overpaid"
    CANCELLED = "cancelled"
    UNKNOWN = "unknown"

    @property
    def grants_entitlement(self) -> bool:
        """True only for states that represent a completed payment."""
        return self in (PaymentStatus.PAID, PaymentStatus.OVERPAID)


class ProviderError(RuntimeError):
    """Raised when a provider call fails or returns malformed data."""


@dataclass(frozen=True)
class CheckoutSession:
    reference_id: str
    checkout_url: str
    host: str = ""


@dataclass(frozen=True)
class PaymentSnapshot:
    reference_id: str
    status: PaymentStatus
    raw_status: str
    invoice_ref: str = ""
    customer_id: str = ""
    amount_usd: float | None = None
    paid_amount_usd: float | None = None
    currency: str = ""


@dataclass(frozen=True)
class WebhookEvent:
    """A normalized, deduplicated webhook notification."""

    provider: str
    reference_id: str
    invoice_ref: str
    status: PaymentStatus
    raw_status: str
    dedup_key: str
    event_type: str
    amount_usd: float | None = None
    paid_amount_usd: float | None = None
    currency: str = ""
    customer_id: str = ""
    timestamp: int | None = None


class PaymentProvider(Protocol):
    """Contract every payment provider adapter must satisfy."""

    name: str

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
    ) -> CheckoutSession: ...

    def get_payment(self, reference_id: str) -> PaymentSnapshot: ...

    def verify_webhook(self, raw_body: bytes, headers: Mapping[str, str]) -> bool: ...

    def parse_webhook(self, raw_body: bytes, headers: Mapping[str, str]) -> WebhookEvent: ...


def is_trusted_checkout_url(url: str, base_url: str) -> bool:
    """Open-redirect guard: a checkout URL must belong to the provider host.

    Only ``http``/``https`` URLs whose host equals the configured provider host
    are accepted. Anything else (javascript:, data:, foreign host, relative)
    is rejected.
    """
    if not url or not base_url:
        return False
    try:
        target = urlparse(url)
        base = urlparse(base_url)
    except ValueError:
        return False
    if target.scheme not in ("http", "https"):
        return False
    if not target.hostname or not base.hostname:
        return False
    return target.hostname.lower() == base.hostname.lower()


def to_float(value) -> float | None:
    """Parse a provider monetary value (JSON string/number) safely."""
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
