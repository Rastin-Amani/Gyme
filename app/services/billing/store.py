"""PocketBase data access for billing (admin-only collections).

All reads/writes go through the dedicated **admin** client
(:func:`app.pb.get_admin_pb`) because these collections have no public API
rules: the browser can never create invoices, flip payment status, mint
credits, or read another gym's billing records.

Amounts are stored in USD (``price_usd`` / ``amount_usd``). Seat credits are
integer deltas in an append-only ``credit_transactions`` ledger; historical
entries are never edited — corrections are compensating rows.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from types import SimpleNamespace

from pocketbase.errors import ClientResponseError

from app.security import pb_escape

logger = logging.getLogger(__name__)

PRODUCTS = "billing_products"
INVOICES = "billing_invoices"
EVENTS = "billing_events"
LEDGER = "credit_transactions"

# Invoice lifecycle states (internal, provider-agnostic).
INVOICE_PENDING = "pending"  # created locally, provider call not yet confirmed
INVOICE_AWAITING = "awaiting"  # provider link issued, no deposit yet
INVOICE_PARTIALLY_PAID = "partially_paid"
INVOICE_PAID = "paid"
INVOICE_OVERPAID = "overpaid"
INVOICE_CANCELLED = "cancelled"
INVOICE_FAILED = "failed"
INVOICE_EXPIRED = "expired"
INVOICE_REFUNDED = "refunded"

TERMINAL_STATES = {
    INVOICE_PAID,
    INVOICE_OVERPAID,
    INVOICE_CANCELLED,
    INVOICE_EXPIRED,
    INVOICE_REFUNDED,
}

# Transitions that may never downgrade a settled invoice.
_FORWARD_ONLY_FROM_PAID = True


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S.000Z")


def _attr(record, name, default=None):
    if record is None:
        return default
    value = getattr(record, name, None)
    if value is None and isinstance(record, dict):
        value = record.get(name)
    return default if value is None else value


# ---------------------------------------------------------------------------
# Products
# ---------------------------------------------------------------------------
def list_products(pb, active_only: bool = True) -> list:
    try:
        flt = "active=true" if active_only else ""
        return pb.collection(PRODUCTS).get_full_list(
            query_params={"filter": flt, "sort": "+sort_order,+price_usd"}
        )
    except Exception as exc:  # collection may not exist yet
        logger.warning("billing.list_products_failed", extra={"error": str(exc)})
        return []


def get_product(pb, key: str):
    safe = pb_escape(str(key or "")[:64])
    if not safe:
        return None
    try:
        return pb.collection(PRODUCTS).get_first_list_item(f'key="{safe}"')
    except ClientResponseError:
        return None


# ---------------------------------------------------------------------------
# Invoices
# ---------------------------------------------------------------------------
def create_invoice(pb, data: dict):
    return pb.collection(INVOICES).create(data)


def get_invoice(pb, tenant_id: str, invoice_ref: str):
    safe = pb_escape(str(invoice_ref or "")[:64])
    if not safe:
        return None
    try:
        return pb.collection(INVOICES).get_first_list_item(
            f'tenant="{pb_escape(tenant_id)}" && invoice_ref="{safe}"'
        )
    except ClientResponseError:
        return None


def get_invoice_by_reference(pb, reference_id: str):
    """Lookup by provider reference (webhook path, tenant-agnostic)."""
    safe = pb_escape(str(reference_id or "")[:128])
    if not safe:
        return None
    try:
        return pb.collection(INVOICES).get_first_list_item(f'provider_ref="{safe}"')
    except ClientResponseError:
        return None


def get_invoice_by_ref_any_tenant(pb, invoice_ref: str):
    safe = pb_escape(str(invoice_ref or "")[:64])
    if not safe:
        return None
    try:
        return pb.collection(INVOICES).get_first_list_item(f'invoice_ref="{safe}"')
    except ClientResponseError:
        return None


def list_invoices(pb, tenant_id: str, page: int = 1, per_page: int = 20):
    try:
        return pb.collection(INVOICES).get_list(
            page=max(1, page),
            per_page=per_page,
            query_params={
                "filter": f'tenant="{pb_escape(tenant_id)}"',
                "sort": "-created",
            },
        )
    except Exception as exc:
        # Never let a billing-history query take down the page.
        logger.warning("billing.list_invoices_failed", extra={"error": str(exc)})
        return SimpleNamespace(items=[], total_items=0, page=page, per_page=per_page)


def count_open_invoices(pb, tenant_id: str) -> int:
    flt = (
        f'tenant="{pb_escape(tenant_id)}" && '
        f'(status="{INVOICE_PENDING}" || status="{INVOICE_AWAITING}" || '
        f'status="{INVOICE_PARTIALLY_PAID}")'
    )
    try:
        result = pb.collection(INVOICES).get_list(page=1, per_page=1, query_params={"filter": flt})
        return getattr(result, "total_items", getattr(result, "totalItems", 0))
    except Exception:
        return 0


def update_invoice(pb, invoice_id: str, data: dict):
    return pb.collection(INVOICES).update(pb_escape(invoice_id), data)


def list_invoices_for_reconcile(pb, limit: int = 50) -> list:
    """Invoices that are not settled and might need provider reconciliation."""
    flt = (
        f'(status="{INVOICE_PENDING}" || status="{INVOICE_AWAITING}" || '
        f'status="{INVOICE_PARTIALLY_PAID}") && provider_ref!=""'
    )
    try:
        return pb.collection(INVOICES).get_full_list(
            query_params={"filter": flt, "sort": "+created", "perPage": str(limit)}
        )
    except Exception:
        return []


# ---------------------------------------------------------------------------
# Webhook events (idempotency)
# ---------------------------------------------------------------------------
def record_event_once(pb, data: dict) -> bool:
    """Insert a webhook event; return True if newly recorded, False if duplicate.

    Uniqueness is enforced by the ``dedup_key`` unique index. A duplicate
    insert raises a PocketBase 400 validation error, which we treat as "already
    handled" — the caller must not fulfill twice.
    """
    try:
        pb.collection(EVENTS).create(data)
        return True
    except ClientResponseError as exc:
        if exc.status == 400:
            return False
        raise


def mark_event_processed(pb, event_id: str, processed: bool, error: str = ""):
    try:
        pb.collection(EVENTS).update(
            pb_escape(event_id),
            {"processed": processed, "error": error[:500]},
        )
    except Exception as exc:
        logger.warning("billing.mark_event_failed", extra={"error": str(exc)})


# ---------------------------------------------------------------------------
# Credit ledger (append-only)
# ---------------------------------------------------------------------------
def add_ledger_entry(pb, data: dict):
    """Append a ledger row. ``idempotency_key`` (unique index) prevents doubles."""
    try:
        return pb.collection(LEDGER).create(data)
    except ClientResponseError as exc:
        if exc.status == 400:
            # Duplicate idempotency key → the grant already happened.
            logger.info("billing.ledger_duplicate", extra={"key": data.get("idempotency_key")})
            return None
        raise


def ledger_balance(pb, tenant_id: str) -> int:
    """Net seat credits for a tenant (grants positive, revocations negative)."""
    try:
        rows = pb.collection(LEDGER).get_full_list(
            query_params={
                "filter": f'tenant="{pb_escape(tenant_id)}" && status="posted"',
                "fields": "delta",
            }
        )
    except Exception as exc:
        logger.warning("billing.ledger_read_failed", extra={"error": str(exc)})
        return 0
    total = 0
    for row in rows:
        try:
            total += int(_attr(row, "delta", 0) or 0)
        except (TypeError, ValueError):
            continue
    return total


def has_grant_for_invoice(pb, invoice_ref: str) -> bool:
    safe = pb_escape(str(invoice_ref or "")[:64])
    if not safe:
        return False
    try:
        row = pb.collection(LEDGER).get_first_list_item(f'invoice_ref="{safe}"')
        return row is not None
    except ClientResponseError:
        return False
