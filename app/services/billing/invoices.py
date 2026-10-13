"""Billing orchestration: checkout creation, payment confirmation, entitlements.

Provider-agnostic. The only provider-specific code lives in
``app/services/billing/payram.py``. This module owns:

- invoice creation + trusted pricing (never client-supplied),
- signature-verified webhook processing with durable idempotency,
- authoritative status reconciliation,
- exactly-once seat-credit fulfillment (append-only ledger),
- manual refund workflow (compensating ledger entry).
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone

from app.services.billing import store
from app.services.billing.config import get_config
from app.services.billing.payram import PayRamProvider
from app.services.billing.provider import (
    PaymentProvider,
    PaymentStatus,
    ProviderError,
)

logger = logging.getLogger(__name__)


class BillingError(RuntimeError):
    """User-facing billing failure (message is safe to show)."""


class BillingDisabled(BillingError):
    pass


class WebhookVerificationError(RuntimeError):
    """Webhook failed signature verification."""


# Normalized provider status -> internal invoice status.
_INVOICE_STATUS = {
    PaymentStatus.AWAITING: store.INVOICE_AWAITING,
    PaymentStatus.PARTIALLY_PAID: store.INVOICE_PARTIALLY_PAID,
    PaymentStatus.PAID: store.INVOICE_PAID,
    PaymentStatus.OVERPAID: store.INVOICE_OVERPAID,
    PaymentStatus.CANCELLED: store.INVOICE_CANCELLED,
}


def get_provider() -> PaymentProvider:
    config = get_config()
    if not config.enabled:
        raise BillingDisabled("Billing is not enabled.")
    if not config.payram_configured:
        raise BillingError("Payment provider is not configured.")
    return PayRamProvider(
        base_url=config.payram_base_url,
        api_key=config.payram_api_key,
        webhook_secret=config.payram_webhook_secret,
        timeout=config.payram_timeout,
    )


def _new_invoice_ref() -> str:
    return "INV-" + uuid.uuid4().hex[:16].upper()


def _rfc3339(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------------------
# Checkout creation
# ---------------------------------------------------------------------------
def create_checkout(pb, *, tenant_id: str, user, product_key: str) -> dict:
    """Create an internal invoice + a PayRam checkout link. Returns the URL.

    The amount and seat quantity come from the trusted product record; nothing
    from the client is trusted except the product key (validated against the DB).
    """
    config = get_config()
    provider = get_provider()  # raises BillingDisabled/BillingError

    product = store.get_product(pb, product_key)
    if product is None or str(getattr(product, "active", False)).lower() not in ("true", "1"):
        raise BillingError("This plan is not available for purchase.")

    price = getattr(product, "price_usd", None)
    seats = getattr(product, "seats", None)
    if price is None or seats is None:
        raise BillingError("This plan is misconfigured. Please contact support.")
    try:
        price = float(price)
        seats = int(seats)
    except (TypeError, ValueError):
        raise BillingError("This plan is misconfigured. Please contact support.")
    if price <= 0 or seats <= 0:
        raise BillingError("This plan is misconfigured. Please contact support.")

    if store.count_open_invoices(pb, tenant_id) >= config.max_open_invoices:
        raise BillingError(
            "You have too many unpaid invoices. Complete or wait for them to expire."
        )

    invoice_ref = _new_invoice_ref()
    expires_at = _rfc3339(
        datetime.now(timezone.utc) + timedelta(seconds=config.checkout_ttl_seconds)
    )
    currency = str(getattr(product, "currency", "") or config.currency)

    invoice = store.create_invoice(
        pb,
        {
            "tenant": tenant_id,
            "invoice_ref": invoice_ref,
            "user": getattr(user, "id", "") or "",
            "product_key": str(getattr(product, "key", product_key)),
            "product_name": str(getattr(product, "name", product_key)),
            "seats": seats,
            "amount_usd": round(price, 2),
            "currency": currency,
            "status": store.INVOICE_PENDING,
            "provider": provider.name,
            "provider_ref": "",
            "checkout_url": "",
            "provider_status": "",
            "paid_amount_usd": 0,
            "error": "",
            "fulfilled_at": "",
        },
    )

    email = str(getattr(user, "email", "") or "").strip() or f"tenant-{tenant_id}@gyme.local"
    try:
        # ``currency`` on the product is a display/quote label (amounts are always
        # USD). PayRam's ``currency`` param restricts the payment to a crypto
        # token (USDC/USDT/...); a fiat code like "USD" makes it reject the
        # request. We let the customer choose any supported crypto, so we do not
        # send it.
        session = provider.create_checkout(
            invoice_ref=invoice_ref,
            customer_email=email,
            customer_id=str(tenant_id),
            amount_usd=price,
            expires_at=expires_at,
        )
    except ProviderError as exc:
        logger.error("billing.checkout_provider_failed", extra={"error": str(exc)})
        store.update_invoice(
            pb, getattr(invoice, "id"), {"status": store.INVOICE_FAILED, "error": str(exc)[:400]}
        )
        raise BillingError("Could not start checkout. Please try again shortly.") from exc

    store.update_invoice(
        pb,
        getattr(invoice, "id"),
        {
            "provider_ref": session.reference_id,
            "checkout_url": session.checkout_url,
            "status": store.INVOICE_AWAITING,
        },
    )
    logger.info(
        "billing.checkout_created",
        extra={"invoice_ref": invoice_ref, "tenant": tenant_id, "seats": seats},
    )
    return {
        "invoice_ref": invoice_ref,
        "checkout_url": session.checkout_url,
        "amount_usd": price,
        "seats": seats,
    }


# ---------------------------------------------------------------------------
# Fulfillment (exactly-once)
# ---------------------------------------------------------------------------
def _apply_invoice_status(pb, invoice, status: PaymentStatus, paid_amount_usd) -> str:
    """Move an invoice to the internal state for ``status``. Never downgrades
    a settled (paid/overpaid/refunded) invoice back to a pending state."""
    invoice_id = getattr(invoice, "id")
    current = str(getattr(invoice, "status", "") or "")
    target = _INVOICE_STATUS.get(status)

    if status.grants_entitlement:
        # Fulfill seat credits once, guarded by a unique ledger idempotency key.
        invoice_ref = str(getattr(invoice, "invoice_ref", ""))
        seats = int(getattr(invoice, "seats", 0) or 0)
        tenant_id = str(getattr(invoice, "tenant", ""))
        if seats > 0 and tenant_id and invoice_ref:
            store.add_ledger_entry(
                pb,
                {
                    "tenant": tenant_id,
                    "invoice_ref": invoice_ref,
                    "delta": seats,
                    "type": "grant",
                    "status": "posted",
                    "idempotency_key": f"grant:{invoice_ref}",
                    "note": str(getattr(invoice, "product_name", ""))[:200],
                },
            )
        store.update_invoice(
            pb,
            invoice_id,
            {
                "status": target or store.INVOICE_PAID,
                "provider_status": status.value,
                "paid_amount_usd": paid_amount_usd or 0,
                "fulfilled_at": store._now_iso(),
            },
        )
        logger.info(
            "billing.invoice_fulfilled",
            extra={"invoice_ref": invoice_ref, "seats": seats, "status": status.value},
        )
        return target or store.INVOICE_PAID

    # Non-entitling states: only advance if the invoice is not already settled.
    if current in (store.INVOICE_PAID, store.INVOICE_OVERPAID, store.INVOICE_REFUNDED):
        return current
    if target is None:
        return current or store.INVOICE_PENDING
    store.update_invoice(
        pb,
        invoice_id,
        {"status": target, "provider_status": status.value},
    )
    return target


def _resolve_invoice(pb, reference_id: str, invoice_ref: str):
    invoice = None
    if reference_id:
        invoice = store.get_invoice_by_reference(pb, reference_id)
    if invoice is None and invoice_ref:
        invoice = store.get_invoice_by_ref_any_tenant(pb, invoice_ref)
    return invoice


def verify_webhook(raw_body: bytes, headers) -> bool:
    """Provider-only signature check (no DB access).

    Used by the route to reject forged deliveries *before* touching PocketBase,
    so a missing admin credential can never turn a bad signature into a 5xx.
    """
    try:
        provider = get_provider()
    except BillingError:
        return False
    return provider.verify_webhook(raw_body, headers)


def process_webhook(pb, raw_body: bytes, headers) -> dict:
    """Verify, deduplicate, reconcile and fulfill a provider webhook.

    Returns a dict describing the outcome. Raises WebhookVerificationError when
    the signature is invalid (the route maps that to 401).
    """
    provider = get_provider()
    if not provider.verify_webhook(raw_body, headers):
        logger.warning("billing.webhook_signature_invalid")
        raise WebhookVerificationError("invalid signature")
    event = provider.parse_webhook(raw_body, headers)

    recorded = store.record_event_once(
        pb,
        {
            "provider": event.provider,
            "dedup_key": event.dedup_key,
            "invoice_ref": event.invoice_ref,
            "reference_id": event.reference_id,
            "status": event.raw_status,
            "processed": False,
            "error": "",
        },
    )
    if not recorded:
        # Already handled (or concurrently handling) this exact event.
        return {"ok": True, "duplicate": True, "reference_id": event.reference_id}

    invoice = _resolve_invoice(pb, event.reference_id, event.invoice_ref)
    if invoice is None:
        # Payment we do not know about yet (e.g. webhook raced persistence).
        # Durably recorded above; reconciliation will pick it up. Ack to stop retries.
        logger.warning(
            "billing.webhook_unknown_invoice", extra={"reference_id": event.reference_id}
        )
        return {"ok": True, "matched": False, "reference_id": event.reference_id}

    # Confirm against the authoritative provider record where possible.
    status = event.status
    paid = event.paid_amount_usd
    try:
        snapshot = provider.get_payment(event.reference_id)
        status = snapshot.status
        paid = snapshot.paid_amount_usd if snapshot.paid_amount_usd is not None else paid
    except ProviderError as exc:
        # Signature was already verified; fall back to the webhook's own status.
        logger.warning("billing.webhook_verify_lookup_failed", extra={"error": str(exc)})

    _apply_invoice_status(pb, invoice, status, paid)
    return {"ok": True, "matched": True, "status": status.value}


# ---------------------------------------------------------------------------
# Reconciliation (return page + recovery)
# ---------------------------------------------------------------------------
def reconcile_invoice(pb, invoice) -> str:
    """Refresh one invoice from the provider and apply transitions."""
    reference = str(getattr(invoice, "provider_ref", "") or "")
    if not reference:
        return str(getattr(invoice, "status", "") or "")
    try:
        snapshot = get_provider().get_payment(reference)
    except (BillingError, ProviderError) as exc:
        logger.warning("billing.reconcile_failed", extra={"error": str(exc)})
        return str(getattr(invoice, "status", "") or "")
    return _apply_invoice_status(pb, invoice, snapshot.status, snapshot.paid_amount_usd)


def reconcile_tenant(pb, tenant_id: str) -> None:
    """Best-effort reconciliation of a tenant's unsettled invoices."""
    for invoice in store.list_invoices_for_reconcile(pb):
        if str(getattr(invoice, "tenant", "")) != str(tenant_id):
            continue
        reconcile_invoice(pb, invoice)


# ---------------------------------------------------------------------------
# Refund (manual workflow; PayRam has no automated crypto refund API)
# ---------------------------------------------------------------------------
def refund_invoice(pb, tenant_id: str, invoice_ref: str) -> dict:
    """Mark an invoice refunded and reverse its seat grant.

    Reversal is a *compensating* negative ledger row — history is never edited.
    This does not move crypto; it records the operator-confirmed refund so
    entitlements and reports stay correct.
    """
    invoice = store.get_invoice(pb, tenant_id, invoice_ref)
    if invoice is None:
        raise BillingError("Invoice not found.")
    current = str(getattr(invoice, "status", "") or "")
    if current == store.INVOICE_REFUNDED:
        return {"ok": True, "already": True}
    if current not in (store.INVOICE_PAID, store.INVOICE_OVERPAID):
        raise BillingError("Only paid invoices can be refunded.")

    seats = int(getattr(invoice, "seats", 0) or 0)
    store.add_ledger_entry(
        pb,
        {
            "tenant": tenant_id,
            "invoice_ref": invoice_ref,
            "delta": -seats,
            "type": "refund",
            "status": "posted",
            "idempotency_key": f"refund:{invoice_ref}",
            "note": "manual refund",
        },
    )
    store.update_invoice(pb, getattr(invoice, "id"), {"status": store.INVOICE_REFUNDED})
    logger.info("billing.invoice_refunded", extra={"invoice_ref": invoice_ref})
    return {"ok": True}
