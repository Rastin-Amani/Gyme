"""Billing unit + integration tests (no live PocketBase, no real payments).

The app's other suites are static source-inspection tests because booting
``TenantMiddleware`` would hit PocketBase. Billing logic is pure enough to test
directly: provider status mapping, signature verification, trusted pricing,
webhook idempotency, exactly-once fulfillment, refunds, and seat accounting.

Run: pytest -q
"""

import hashlib
import hmac
import json
from types import SimpleNamespace

import pytest

from app.services.billing import store
from app.services.billing.config import get_config, reset_config_cache
from app.services.billing.provider import (
    CheckoutSession,
    PaymentSnapshot,
    PaymentStatus,
    ProviderError,
    is_trusted_checkout_url,
)


# ---------------------------------------------------------------------------
# Provider status mapping
# ---------------------------------------------------------------------------
def test_payram_status_mapping():
    from app.services.billing.payram import map_status

    assert map_status("OPEN") is PaymentStatus.AWAITING
    assert map_status("PARTIALLY_FILLED") is PaymentStatus.PARTIALLY_PAID
    assert map_status("FILLED") is PaymentStatus.PAID
    assert map_status("OVER_FILLED") is PaymentStatus.OVERPAID
    assert map_status("CANCELLED") is PaymentStatus.CANCELLED
    assert map_status("garbage") is PaymentStatus.UNKNOWN
    assert map_status(None) is PaymentStatus.UNKNOWN


def test_only_paid_states_grant_entitlement():
    assert PaymentStatus.PAID.grants_entitlement
    assert PaymentStatus.OVERPAID.grants_entitlement
    assert not PaymentStatus.PARTIALLY_PAID.grants_entitlement
    assert not PaymentStatus.AWAITING.grants_entitlement
    assert not PaymentStatus.CANCELLED.grants_entitlement
    assert not PaymentStatus.UNKNOWN.grants_entitlement


# ---------------------------------------------------------------------------
# Checkout URL safety (open-redirect guard)
# ---------------------------------------------------------------------------
def test_trusted_checkout_url():
    base = "https://pay.example.com"
    assert is_trusted_checkout_url("https://pay.example.com/payments?ref=1", base)
    assert not is_trusted_checkout_url("https://evil.com/payments", base)
    assert not is_trusted_checkout_url("javascript:alert(1)", base)
    assert not is_trusted_checkout_url("data:text/html,x", base)
    assert not is_trusted_checkout_url("/relative", base)
    assert not is_trusted_checkout_url("", base)


# ---------------------------------------------------------------------------
# Webhook signature verification
# ---------------------------------------------------------------------------
def _provider(secret="s3cret", api_key="apikey"):
    from app.services.billing.payram import PayRamProvider

    return PayRamProvider("https://pay.example.com", api_key, secret)


def test_webhook_signature_valid_and_invalid():
    provider = _provider(secret="s3cret", api_key="apikey")
    body = b'{"reference_id":"r1","status":"FILLED"}'
    good = "sha256=" + hmac.new(b"s3cret", body, hashlib.sha256).hexdigest()

    assert provider.verify_webhook(body, {"X-Payram-Signature": good}) is True
    assert provider.verify_webhook(body, {"X-Payram-Signature": "sha256=deadbeef"}) is False
    assert provider.verify_webhook(body, {}) is False
    # tampered body fails even with a signature header
    assert provider.verify_webhook(body + b" ", {"X-Payram-Signature": good}) is False


def test_webhook_legacy_api_key_header():
    provider = _provider(secret="s3cret", api_key="apikey")
    body = b"{}"
    assert provider.verify_webhook(body, {"API-KEY": "apikey"}) is True
    assert provider.verify_webhook(body, {"API-KEY": "wrong"}) is False


def test_webhook_secret_defaults_to_api_key():
    # No explicit webhook secret -> signs with the API key (PayRam's default).
    provider = _provider(secret="", api_key="apikey")
    body = b'{"x":1}'
    sig = "sha256=" + hmac.new(b"apikey", body, hashlib.sha256).hexdigest()
    assert provider.verify_webhook(body, {"X-Payram-Signature": sig}) is True


def test_parse_webhook_dedup_key_and_fields():
    provider = _provider()
    body = json.dumps(
        {
            "reference_id": "ref-9",
            "invoice_id": "INV-1",
            "status": "FILLED",
            "filled_amount_in_usd": "29.00",
            "currency": "USDT",
            "customer_id": "t1",
            "timestamp": 1750340282,
        }
    ).encode()
    event = provider.parse_webhook(body, {})
    assert event.reference_id == "ref-9"
    assert event.invoice_ref == "INV-1"
    assert event.status is PaymentStatus.PAID
    assert event.dedup_key == "payram:ref-9:FILLED"
    assert event.paid_amount_usd == 29.0


def test_parse_webhook_rejects_malformed():
    provider = _provider()
    with pytest.raises(ProviderError):
        provider.parse_webhook(b"not json", {})
    with pytest.raises(ProviderError):
        provider.parse_webhook(b'{"status":"FILLED"}', {})  # no reference_id


def test_snapshot_parses_camelcase_status_api():
    # The status API returns camelCase; the webhook is snake_case. Both must work.
    from app.services.billing.payram import snapshot_from_dict

    api = {
        "invoiceID": "INV-9",
        "customerID": "t1",
        "amountInUSD": "5",
        "filledAmountInUSD": "5.00",
        "paymentState": "FILLED",
        "referenceID": "ref-9",
    }
    snap = snapshot_from_dict(api)
    assert snap.status is PaymentStatus.PAID
    assert snap.reference_id == "ref-9"
    assert snap.invoice_ref == "INV-9"
    assert snap.amount_usd == 5.0
    assert snap.paid_amount_usd == 5.0

    hook = {
        "invoice_id": "INV-9",
        "customer_id": "t1",
        "amount": "5",
        "filled_amount_in_usd": "5.00",
        "status": "OVER_FILLED",
        "reference_id": "ref-9",
    }
    snap2 = snapshot_from_dict(hook)
    assert snap2.status is PaymentStatus.OVERPAID
    assert snap2.paid_amount_usd == 5.0


def test_snapshot_open_has_null_filled_amount():
    from app.services.billing.payram import snapshot_from_dict

    snap = snapshot_from_dict(
        {"referenceID": "r", "paymentState": "OPEN", "amountInUSD": "5", "filledAmountInUSD": None}
    )
    assert snap.status is PaymentStatus.AWAITING
    assert snap.paid_amount_usd is None


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
def test_config_disabled_by_default(monkeypatch):
    for var in (
        "BILLING_ENABLED",
        "PAYRAM_BASE_URL",
        "PAYRAM_API_KEY",
        "BILLING_FREE_SEATS",
    ):
        monkeypatch.delenv(var, raising=False)
    reset_config_cache()
    config = get_config()
    assert config.enabled is False
    assert config.free_seats == 5
    reset_config_cache()


def test_config_requires_provider_when_enabled(monkeypatch):
    monkeypatch.setenv("BILLING_ENABLED", "true")
    monkeypatch.delenv("PAYRAM_BASE_URL", raising=False)
    monkeypatch.delenv("PAYRAM_API_KEY", raising=False)
    reset_config_cache()
    with pytest.raises(RuntimeError):
        get_config()
    reset_config_cache()


def test_config_free_seats_parsing(monkeypatch):
    monkeypatch.setenv("BILLING_FREE_SEATS", "12")
    monkeypatch.delenv("BILLING_ENABLED", raising=False)
    reset_config_cache()
    assert get_config().free_seats == 12
    monkeypatch.setenv("BILLING_FREE_SEATS", "not-a-number")
    reset_config_cache()
    with pytest.raises(RuntimeError):
        get_config()
    reset_config_cache()


# ---------------------------------------------------------------------------
# Checkout creation: trusted pricing + provider failure handling
# ---------------------------------------------------------------------------
class _FakeProvider:
    name = "payram"

    def __init__(self, fail=False):
        self.fail = fail
        self.calls = []

    def create_checkout(self, **kwargs):
        self.calls.append(kwargs)
        if self.fail:
            raise ProviderError("boom")
        return CheckoutSession(
            reference_id="ref-1",
            checkout_url="https://pay.example.com/payments?reference_id=ref-1",
            host="https://pay.example.com",
        )


def _patch_product(monkeypatch, **overrides):
    base = dict(
        id="prod1",
        key="seats-10",
        name="10 seats",
        active=True,
        price_usd=29.0,
        seats=10,
        currency="USD",
    )
    base.update(overrides)
    product = SimpleNamespace(**base)
    monkeypatch.setattr(store, "get_product", lambda pb, key: product)
    return product


def test_create_checkout_uses_server_side_price(monkeypatch):
    from app.services.billing import invoices

    _patch_product(monkeypatch, price_usd=42.5, seats=7)
    provider = _FakeProvider()
    monkeypatch.setattr(invoices, "get_provider", lambda: provider)
    monkeypatch.setattr(store, "count_open_invoices", lambda pb, tenant: 0)

    updates = []
    monkeypatch.setattr(
        store, "create_invoice", lambda pb, data: SimpleNamespace(id="inv1", **data)
    )
    monkeypatch.setattr(store, "update_invoice", lambda pb, iid, data: updates.append(data))

    result = invoices.create_checkout(
        None, tenant_id="t1", user=SimpleNamespace(id="u1", email="a@b.c"), product_key="seats-10"
    )

    assert result["amount_usd"] == 42.5
    assert result["seats"] == 7
    # provider received the trusted amount, not anything client supplied
    assert provider.calls[0]["amount_usd"] == 42.5
    assert provider.calls[0]["customer_id"] == "t1"
    assert updates[-1]["status"] == store.INVOICE_AWAITING


def test_create_checkout_marks_invoice_failed_on_provider_error(monkeypatch):
    from app.services.billing import invoices

    _patch_product(monkeypatch)
    monkeypatch.setattr(invoices, "get_provider", lambda: _FakeProvider(fail=True))
    monkeypatch.setattr(store, "count_open_invoices", lambda pb, tenant: 0)
    monkeypatch.setattr(
        store, "create_invoice", lambda pb, data: SimpleNamespace(id="inv1", **data)
    )
    updates = []
    monkeypatch.setattr(store, "update_invoice", lambda pb, iid, data: updates.append(data))

    with pytest.raises(invoices.BillingError):
        invoices.create_checkout(
            None,
            tenant_id="t1",
            user=SimpleNamespace(id="u1", email="a@b.c"),
            product_key="seats-10",
        )
    assert updates[-1]["status"] == store.INVOICE_FAILED


def test_create_checkout_rejects_inactive_product(monkeypatch):
    from app.services.billing import invoices

    _patch_product(monkeypatch, active=False)
    monkeypatch.setattr(invoices, "get_provider", lambda: _FakeProvider())
    with pytest.raises(invoices.BillingError):
        invoices.create_checkout(
            None,
            tenant_id="t1",
            user=SimpleNamespace(id="u1", email="a@b.c"),
            product_key="seats-10",
        )


def test_create_checkout_enforces_open_invoice_limit(monkeypatch):
    from app.services.billing import invoices

    _patch_product(monkeypatch)
    monkeypatch.setattr(invoices, "get_provider", lambda: _FakeProvider())
    monkeypatch.setattr(store, "count_open_invoices", lambda pb, tenant: 999)
    with pytest.raises(invoices.BillingError):
        invoices.create_checkout(
            None,
            tenant_id="t1",
            user=SimpleNamespace(id="u1", email="a@b.c"),
            product_key="seats-10",
        )


# ---------------------------------------------------------------------------
# Webhook processing: idempotency + exactly-once fulfillment
# ---------------------------------------------------------------------------
def _paid_invoice():
    return SimpleNamespace(
        id="inv1",
        tenant="t1",
        invoice_ref="INV-1",
        product_name="10 seats",
        seats=10,
        status=store.INVOICE_AWAITING,
        provider_ref="ref-1",
    )


def _webhook_provider(status=PaymentStatus.PAID):
    class P:
        name = "payram"

        def verify_webhook(self, raw, headers):
            return True

        def parse_webhook(self, raw, headers):
            from app.services.billing.provider import WebhookEvent

            return WebhookEvent(
                provider="payram",
                reference_id="ref-1",
                invoice_ref="INV-1",
                status=status,
                raw_status=status.value,
                dedup_key=f"payram:ref-1:{status.value}",
                event_type="payment",
            )

        def get_payment(self, reference_id):
            return PaymentSnapshot(
                reference_id=reference_id,
                status=status,
                raw_status=status.value,
                paid_amount_usd=29.0,
            )

    return P()


def test_webhook_fulfills_once_and_dedups(monkeypatch):
    from app.services.billing import invoices

    invoice = _paid_invoice()
    monkeypatch.setattr(invoices, "get_provider", lambda: _webhook_provider())
    monkeypatch.setattr(store, "get_invoice_by_reference", lambda pb, ref: invoice)

    # First delivery: recorded -> fulfilled.
    monkeypatch.setattr(store, "record_event_once", lambda pb, data: True)
    ledger = []
    monkeypatch.setattr(store, "add_ledger_entry", lambda pb, data: ledger.append(data))
    monkeypatch.setattr(store, "update_invoice", lambda pb, iid, data: None)

    result = invoices.process_webhook(None, b"{}", {})
    assert result["matched"] is True
    assert len(ledger) == 1
    assert ledger[0]["delta"] == 10
    assert ledger[0]["idempotency_key"] == "grant:INV-1"

    # Second delivery: dedup -> no fulfillment.
    monkeypatch.setattr(store, "record_event_once", lambda pb, data: False)
    result2 = invoices.process_webhook(None, b"{}", {})
    assert result2.get("duplicate") is True
    assert len(ledger) == 1  # unchanged


def test_webhook_invalid_signature_raises(monkeypatch):
    from app.services.billing import invoices

    class P:
        name = "payram"

        def verify_webhook(self, raw, headers):
            return False

    monkeypatch.setattr(invoices, "get_provider", lambda: P())
    with pytest.raises(invoices.WebhookVerificationError):
        invoices.process_webhook(None, b"{}", {})


def test_webhook_unknown_invoice_is_recorded_not_fulfilled(monkeypatch):
    from app.services.billing import invoices

    monkeypatch.setattr(invoices, "get_provider", lambda: _webhook_provider())
    monkeypatch.setattr(store, "record_event_once", lambda pb, data: True)
    monkeypatch.setattr(store, "get_invoice_by_reference", lambda pb, ref: None)
    monkeypatch.setattr(store, "get_invoice_by_ref_any_tenant", lambda pb, ref: None)
    ledger = []
    monkeypatch.setattr(store, "add_ledger_entry", lambda pb, data: ledger.append(data))

    result = invoices.process_webhook(None, b"{}", {})
    assert result["matched"] is False
    assert ledger == []


def test_partial_payment_does_not_grant_seats(monkeypatch):
    from app.services.billing import invoices

    invoice = _paid_invoice()
    monkeypatch.setattr(
        invoices, "get_provider", lambda: _webhook_provider(PaymentStatus.PARTIALLY_PAID)
    )
    monkeypatch.setattr(store, "get_invoice_by_reference", lambda pb, ref: invoice)
    monkeypatch.setattr(store, "record_event_once", lambda pb, data: True)
    ledger = []
    monkeypatch.setattr(store, "add_ledger_entry", lambda pb, data: ledger.append(data))
    updates = []
    monkeypatch.setattr(store, "update_invoice", lambda pb, iid, data: updates.append(data))

    invoices.process_webhook(None, b"{}", {})
    assert ledger == []
    assert updates[-1]["status"] == store.INVOICE_PARTIALLY_PAID


def test_late_pending_event_does_not_downgrade_paid(monkeypatch):
    from app.services.billing import invoices

    paid = SimpleNamespace(
        id="inv1", tenant="t1", invoice_ref="INV-1", seats=10, status=store.INVOICE_PAID
    )
    updates = []
    monkeypatch.setattr(store, "update_invoice", lambda pb, iid, data: updates.append(data))
    monkeypatch.setattr(store, "add_ledger_entry", lambda pb, data: None)

    # A stale OPEN event must not knock a paid invoice back to awaiting.
    invoices._apply_invoice_status(None, paid, PaymentStatus.AWAITING, None)
    assert updates == []


# ---------------------------------------------------------------------------
# Refunds
# ---------------------------------------------------------------------------
def test_refund_records_compensating_entry(monkeypatch):
    from app.services.billing import invoices

    paid = SimpleNamespace(id="inv1", invoice_ref="INV-1", seats=10, status=store.INVOICE_PAID)
    monkeypatch.setattr(store, "get_invoice", lambda pb, tenant, ref: paid)
    ledger = []
    monkeypatch.setattr(store, "add_ledger_entry", lambda pb, data: ledger.append(data))
    monkeypatch.setattr(store, "update_invoice", lambda pb, iid, data: None)

    invoices.refund_invoice(None, "t1", "INV-1")
    assert ledger[0]["delta"] == -10
    assert ledger[0]["type"] == "refund"


def test_refund_rejects_unpaid(monkeypatch):
    from app.services.billing import invoices

    unpaid = SimpleNamespace(
        id="inv1", invoice_ref="INV-1", seats=10, status=store.INVOICE_AWAITING
    )
    monkeypatch.setattr(store, "get_invoice", lambda pb, tenant, ref: unpaid)
    with pytest.raises(invoices.BillingError):
        invoices.refund_invoice(None, "t1", "INV-1")


# ---------------------------------------------------------------------------
# Seat accounting
# ---------------------------------------------------------------------------
class _CountPB:
    def __init__(self, total):
        self._total = total

    def collection(self, name):
        outer = self

        class C:
            def get_list(self, **kwargs):
                return SimpleNamespace(total_items=outer._total)

        return C()


def test_seat_summary_capacity(monkeypatch):
    from app.services.billing import seats

    monkeypatch.setenv("BILLING_FREE_SEATS", "5")
    reset_config_cache()
    monkeypatch.setattr(store, "ledger_balance", lambda pb, tenant: 10)

    summary = seats.seat_summary(_CountPB(7), "t1")
    assert summary["free_seats"] == 5
    assert summary["purchased_seats"] == 10
    assert summary["capacity"] == 15
    assert summary["used"] == 7
    assert summary["remaining"] == 8
    reset_config_cache()


def test_has_free_seat_at_capacity(monkeypatch):
    from app.services.billing import seats

    monkeypatch.setenv("BILLING_FREE_SEATS", "5")
    reset_config_cache()
    monkeypatch.setattr(store, "ledger_balance", lambda pb, tenant: 0)

    allowed, summary = seats.has_free_seat(_CountPB(5), "t1")
    assert allowed is False
    assert summary["remaining"] == 0
    reset_config_cache()


def test_ledger_balance_sums_deltas(monkeypatch):
    class PB:
        def collection(self, name):
            class C:
                def get_full_list(self, **kwargs):
                    return [
                        SimpleNamespace(delta=10),
                        SimpleNamespace(delta=-3),
                        SimpleNamespace(delta=5),
                    ]

            return C()

    assert store.ledger_balance(PB(), "t1") == 12


# ---------------------------------------------------------------------------
# Static contracts (source inspection — consistent with the repo's suites)
# ---------------------------------------------------------------------------
def test_webhook_path_is_public_and_csrf_exempt():
    src = open("app/middleware.py").read()
    assert '"/webhooks/"' in src
    # appears in both PUBLIC_PATHS and CSRF_EXEMPT_PATHS
    assert src.count('"/webhooks/"') >= 2


def test_trainee_creation_enforces_seat_limit():
    src = open("app/routes/trainee.py").read()
    create_src = src[src.index("def trainee_create") : src.index("def trainee_update")]
    assert "seat_service.has_free_seat" in create_src
    assert "tenant_seat_lock" in create_src
    assert "409" in create_src


def test_trainee_form_shows_paywall():
    src = open("app/routes/trainee.py").read()
    form_src = src[src.index("def trainees_new_form") : src.index("def show_trainee_detail")]
    assert "at_capacity" in form_src
    assert "seat_service.seat_summary" in form_src
    tpl = open("app/templates/forms/trainees_form.html").read()
    assert "components/billing_paywall.html" in tpl
    assert "at_capacity" in tpl


def test_billing_routes_are_owner_only():
    src = open("app/routes/billing.py").read()
    assert "_require_owner" in src
    assert 'role != "owner"' in src
    # refund is owner-gated too
    refund_src = src[src.index("def billing_refund") :]
    assert "_require_owner" in refund_src


def test_billing_collections_are_admin_only():
    src = open("pb_migrations/1750000000_billing.js").read()
    # every billing collection locks all rules
    assert src.count("listRule: null") >= 4
    assert src.count("createRule: null") >= 4
    assert src.count("updateRule: null") >= 4
    # idempotency enforced at the DB level
    assert "idx_billing_events_dedup" in src
    assert "idx_credit_tx_idem" in src


def test_no_public_api_key_in_frontend_bundle():
    # The PayRam key is server-only; it must never appear in JS/templates.
    import glob

    for path in glob.glob("app/static/**/*.js", recursive=True) + glob.glob(
        "app/templates/**/*.html", recursive=True
    ):
        content = open(path, encoding="utf-8", errors="ignore").read()
        assert "PAYRAM_API_KEY" not in content, path
        assert "payram_api_key" not in content, path


# ---------------------------------------------------------------------------
# End-to-end webhook over the real HTTP stack (public route, no PocketBase)
# ---------------------------------------------------------------------------
def _enable_billing(monkeypatch, api_key="apikey"):
    monkeypatch.setenv("BILLING_ENABLED", "true")
    monkeypatch.setenv("PAYRAM_BASE_URL", "https://pay.example.com")
    monkeypatch.setenv("PAYRAM_API_KEY", api_key)
    monkeypatch.delenv("PAYRAM_WEBHOOK_SECRET", raising=False)
    reset_config_cache()


def test_webhook_unsigned_is_401(monkeypatch):
    from fastapi.testclient import TestClient

    from app.main import app

    _enable_billing(monkeypatch)
    client = TestClient(app, follow_redirects=False)
    r = client.post("/webhooks/payram", json={"reference_id": "r", "status": "FILLED"})
    assert r.status_code == 401
    reset_config_cache()


def test_webhook_valid_signature_is_accepted(monkeypatch):
    from fastapi.testclient import TestClient

    from app.main import app
    from app.routes import billing as billing_routes
    from app.services.billing import invoices

    _enable_billing(monkeypatch)
    monkeypatch.setattr(billing_routes, "get_admin_pb", lambda: object())
    monkeypatch.setattr(invoices, "process_webhook", lambda pb, raw, headers: {"ok": True})
    body = json.dumps({"reference_id": "r1", "status": "FILLED"}).encode()
    sig = "sha256=" + hmac.new(b"apikey", body, hashlib.sha256).hexdigest()

    client = TestClient(app, follow_redirects=False)
    r = client.post("/webhooks/payram", content=body, headers={"X-Payram-Signature": sig})
    assert r.status_code == 200
    assert r.json()["ok"] is True
    reset_config_cache()


def test_webhook_oversized_body_is_rejected(monkeypatch):
    from fastapi.testclient import TestClient

    from app.main import app

    _enable_billing(monkeypatch)
    client = TestClient(app, follow_redirects=False)
    r = client.post("/webhooks/payram", content=b"x" * (70 * 1024))
    assert r.status_code == 413
    reset_config_cache()


# ---------------------------------------------------------------------------
# Template rendering (guards against gettext/interpolation mistakes)
# ---------------------------------------------------------------------------
def test_billing_components_render():
    from app.templates import templates

    env = templates.env
    invoice = SimpleNamespace(
        invoice_ref="INV-1",
        product_name="10 seats",
        status="paid",
        seats=10,
        amount_usd=29.0,
        currency="USD",
        created="2026-10-13 10:00:00.000Z",
        fulfilled_at="2026-10-13 10:05:00.000Z",
    )
    html = env.get_template("components/billing_invoice_row.html").render(
        invoice=invoice, currency="USD"
    )
    assert "INV-1" in html and "29.00" in html

    paywall = env.get_template("components/billing_paywall.html").render(
        seats={"used": 5, "capacity": 5}
    )
    assert "seat-limit-banner" in paywall

    status = env.get_template("components/billing_status.html").render(is_paid=True, status="paid")
    assert "Payment confirmed" in status

    pending = env.get_template("components/billing_status.html").render(
        is_paid=False, status="awaiting"
    )
    assert "Waiting for payment" in pending


def test_all_templates_compile():
    """Every template must compile (catches Jinja syntax errors cheaply)."""
    import glob

    from app.templates import templates

    names = [
        p[len("app/templates/") :] for p in glob.glob("app/templates/**/*.html", recursive=True)
    ]
    assert names, "no templates found"
    for name in names:
        templates.env.get_template(name)
