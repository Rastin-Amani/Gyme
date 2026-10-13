"""Billing routes: overview, checkout, return handling, webhook, refunds.

Owner-only except the public provider webhook. All billing data access uses the
server-side admin client; the browser never touches billing collections
directly.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Form, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

from app.i18n import _
from app.pb import get_admin_pb
from app.services.billing import invoices as billing
from app.services.billing import seats, store
from app.services.billing.config import get_config
from app.templates import templates
from app.utils import hx_toast

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Billing"])


def _require_owner(request: Request):
    """Return the user if owner, else a redirect/403 response."""
    user = getattr(request.state, "user", None)
    if user is None:
        return None, RedirectResponse(url="/login", status_code=303)
    role = getattr(user, "role", None)
    if role == "trainee":
        return None, RedirectResponse(url="/user/dashboard", status_code=303)
    if role != "owner":
        return None, HTMLResponse("", status_code=403)
    return user, None


def _is_htmx(request: Request) -> bool:
    return request.headers.get("hx-request") == "true"


def _overview_context(request: Request) -> dict:
    tenant = request.state.tenant
    user = request.state.user
    config = get_config()
    admin = get_admin_pb()
    tenant_id = tenant.id

    products = store.list_products(admin, active_only=True) if config.enabled else []
    invoices_page = store.list_invoices(admin, tenant_id, page=1, per_page=20)
    invoices_list = getattr(invoices_page, "items", invoices_page)

    return {
        "title": _("Billing"),
        "tenant": tenant,
        "user": user,
        "seats": seats.seat_summary(admin, tenant_id),
        "products": products,
        "invoices": invoices_list,
        "billing_enabled": config.enabled,
        "provider_ready": config.payram_configured,
        "currency": config.currency,
    }


@router.get("/billing")
def billing_overview(request: Request):
    user, denial = _require_owner(request)
    if denial:
        return denial
    return templates.TemplateResponse(
        request=request,
        name="pages/owner/billing/billing.html",
        context=_overview_context(request),
    )


@router.post("/billing/checkout")
def billing_checkout(request: Request, product_key: str = Form(...)):
    user, denial = _require_owner(request)
    if denial:
        if _is_htmx(request):
            return HTMLResponse("", headers=hx_toast(_("Access denied"), "error"), status_code=403)
        return denial

    tenant_id = request.state.tenant.id
    admin = get_admin_pb()
    try:
        result = billing.create_checkout(
            admin, tenant_id=tenant_id, user=user, product_key=str(product_key)[:64]
        )
    except billing.BillingDisabled:
        return HTMLResponse(
            "", headers=hx_toast(_("Billing is currently unavailable."), "error"), status_code=400
        )
    except billing.BillingError as exc:
        return HTMLResponse("", headers=hx_toast(str(exc), "error"), status_code=400)
    except Exception:
        logger.exception("billing.checkout_failed", extra={"tenant": tenant_id})
        return HTMLResponse(
            "",
            headers=hx_toast(_("Could not start checkout. Please try again shortly."), "error"),
            status_code=500,
        )

    # Redirect the browser to the (validated, provider-hosted) checkout URL.
    headers = hx_toast(_("Redirecting to secure checkout…"), "info")
    headers["HX-Redirect"] = result["checkout_url"]
    return HTMLResponse("", headers=headers)


@router.get("/billing/return")
def billing_return(request: Request, invoice: str = Query("")):
    user, denial = _require_owner(request)
    if denial:
        return denial

    tenant_id = request.state.tenant.id
    admin = get_admin_pb()
    record = store.get_invoice(admin, tenant_id, invoice) if invoice else None

    # Reconcile with the provider so the page reflects confirmed state, not the
    # browser's optimistic assumption.
    if record is not None and str(getattr(record, "status", "")) not in store.TERMINAL_STATES:
        billing.reconcile_invoice(admin, record)
        record = store.get_invoice(admin, tenant_id, invoice)

    status = str(getattr(record, "status", "") or "") if record else ""
    return templates.TemplateResponse(
        request=request,
        name="pages/owner/billing/return.html",
        context={
            "title": _("Payment status"),
            "tenant": request.state.tenant,
            "user": user,
            "invoice": record,
            "invoice_ref": invoice,
            "status": status,
            "is_paid": status in (store.INVOICE_PAID, store.INVOICE_OVERPAID),
            "is_terminal": status in store.TERMINAL_STATES,
        },
    )


@router.get("/billing/checkout/{invoice_ref}/status")
def billing_status_fragment(request: Request, invoice_ref: str):
    user, denial = _require_owner(request)
    if denial:
        return denial

    tenant_id = request.state.tenant.id
    admin = get_admin_pb()
    record = store.get_invoice(admin, tenant_id, invoice_ref)
    status = str(getattr(record, "status", "") or "") if record else ""
    if record is not None and status not in store.TERMINAL_STATES:
        billing.reconcile_invoice(admin, record)
        record = store.get_invoice(admin, tenant_id, invoice_ref)
        status = str(getattr(record, "status", "") or "") if record else ""

    is_paid = status in (store.INVOICE_PAID, store.INVOICE_OVERPAID)
    inner = templates.get_template("components/billing_status.html").render(
        invoice=record, invoice_ref=invoice_ref, status=status, is_paid=is_paid
    )

    headers = {}
    if status in store.TERMINAL_STATES:
        # Replace the polling container so the poll stops; announce the outcome.
        inner = f'<div hx-swap-oob="outerHTML:#payment-status">{inner}</div>'
        if is_paid:
            headers = hx_toast(_("Payment confirmed. Your seats have been added."), "success")
    return HTMLResponse(content=inner, headers=headers)


@router.post("/billing/invoices/{invoice_ref}/refund")
def billing_refund(request: Request, invoice_ref: str):
    """Owner-initiated manual refund marker (operator confirms the crypto refund
    out-of-band; this reverses the seat entitlement and records the state)."""
    user, denial = _require_owner(request)
    if denial:
        return denial

    admin = get_admin_pb()
    try:
        billing.refund_invoice(admin, request.state.tenant.id, invoice_ref)
    except billing.BillingError as exc:
        return HTMLResponse("", headers=hx_toast(str(exc), "error"), status_code=400)
    return HTMLResponse("", headers=hx_toast(_("Refund recorded."), "success"))


# ---------------------------------------------------------------------------
# Provider webhook (public, unauthenticated, signature-verified)
# ---------------------------------------------------------------------------
@router.post("/webhooks/payram")
async def payram_webhook(request: Request):
    raw = await request.body()
    if len(raw) > 64 * 1024:  # bound the request size
        return JSONResponse({"ok": False}, status_code=413)
    # Reject forged deliveries before any database access.
    if not billing.verify_webhook(raw, request.headers):
        return JSONResponse({"ok": False}, status_code=401)
    try:
        admin = get_admin_pb()
        result = billing.process_webhook(admin, raw, request.headers)
    except billing.WebhookVerificationError:
        return JSONResponse({"ok": False}, status_code=401)
    except Exception:
        # Never leak details; PayRam retries on >=400, which is what we want
        # for transient failures (the event is only durably recorded once past
        # verification, so a retry after a crash is safe).
        logger.exception("billing.webhook_failed")
        return JSONResponse({"ok": False}, status_code=500)
    return JSONResponse({"ok": True, **result})
