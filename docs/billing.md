# Billing, Payments & Seat Entitlements

**Model:** active-trainee **seats** per gym (tenant), one-time PayRam crypto
purchases. **Status:** implemented and tested against mocked providers; no real
payment has been executed. PocketBase-side setup is verified by inspection of
the migration, not by running it (no PocketBase in this environment).

---

## 1. What is monetized

Gyme is sold to gyms. The monetized resource is an **active trainee seat**:

```
capacity  = BILLING_FREE_SEATS + net purchased seat credits
used      = trainees with status="active" in the tenant
remaining = max(0, capacity - used)
```

- A new gym gets `BILLING_FREE_SEATS` (default 5) active trainees free, forever.
- Seat packs (`billing_products`) are one-time purchases that add **permanent**
  seat capacity, recorded in an append-only ledger.
- Trainee creation (and only creation — reactivation is not exposed by the UI)
  is blocked server-side when `used >= capacity`. Deleting a trainee frees a seat.

Why not subscriptions: PayRam has **no recurring billing**. Implementing
"monthly plans" would mean inventing automatic charges the provider cannot do.
Seat packs are a one-time, honest model. A subscription layer can be added later
behind the same provider interface (see §9).

---

## 2. Architecture

```
Route (app/routes/billing.py)
   │  owner-only, HTMX; webhook is public + signature-verified
   ▼
Billing service (app/services/billing/)
   ├─ config.py    env config, validated, secrets live here only
   ├─ provider.py  PaymentProvider contract + normalized states + URL guard
   ├─ payram.py    PayRam adapter (the ONLY provider-specific code)
   ├─ store.py     PocketBase access (admin-only collections)
   ├─ seats.py     capacity math + per-tenant enforcement lock
   └─ invoices.py  checkout, webhook processing, reconciliation, refunds
   ▼
PocketBase (admin client only)  +  PayRam REST API (server-side requests)
```

The rest of the app depends on `invoices`/`seats`, never on PayRam's schema.

### Invoice lifecycle

```
pending → awaiting → paid | overpaid        (grant seats exactly once)
                  ↘ partially_paid → paid
                  ↘ cancelled | expired | failed
paid → refunded                              (compensating ledger entry)
```

State is **forward-only** for settled invoices: a late/duplicate `OPEN` webhook
can never downgrade a `paid` invoice (unit-tested).

---

## 3. PocketBase schema

Four collections, all **admin-only** (all rules `null`). Created by
`pb_migrations/1750000000_billing.js` (targets PocketBase ≥ 0.23; on older
versions create them via the admin UI with the same fields).

| Collection | Purpose | Key fields |
| --- | --- | --- |
| `billing_products` | purchasable seat packs | `key`(unique), `name`, `description`, `active`, `price_usd`, `seats`, `currency`, `sort_order` |
| `billing_invoices` | internal invoices + provider refs | `tenant`, `invoice_ref`(unique), `user`, `product_key`, `product_name`, `seats`, `amount_usd`, `currency`, `status`, `provider`, `provider_ref`, `checkout_url`, `provider_status`, `paid_amount_usd`, `error`, `fulfilled_at` |
| `billing_events` | webhook idempotency | `provider`, `dedup_key`(unique), `invoice_ref`, `reference_id`, `status`, `processed`, `error` |
| `credit_transactions` | append-only seat ledger | `tenant`, `invoice_ref`, `delta`, `type`, `status`, `idempotency_key`(unique), `note` |

Indexes: unique on `billing_products.key`, `billing_invoices.invoice_ref`,
`billing_events.dedup_key`, `credit_transactions.idempotency_key`; plus lookup
indexes on `billing_invoices.(tenant, provider_ref, status)`,
`billing_events.reference_id`, `credit_transactions.(tenant, invoice_ref)`.

**Why admin-only:** these records are the source of truth for money and
entitlements. Exposing them to the browser (even read-only) risks leaking other
gyms' payments and invites tampering. The app reads/writes them through the
superuser client only.

`billing_invoices.tenant` and `credit_transactions.tenant` are relations to
`tenants` (so per-gym reporting is one filter).

### Applying the schema

```bash
# copy the migration into your PocketBase instance and restart PB, or
pb_migrations/1750000000_billing.js  →  <pb_dir>/pb_migrations/
# PocketBase applies it on next start; rollback drops the four collections only.
```

---

## 4. Configuration

Server-side only. Never commit real values; never expose them to templates/JS.

| Variable | Required | Default | Meaning |
| --- | --- | --- | --- |
| `BILLING_ENABLED` | no | `false` | Master switch. When false, `/billing` still shows seat usage but purchases are disabled and trainee creation is **not** limited. |
| `BILLING_FREE_SEATS` | no | `5` | Free active-trainee allowance per gym. |
| `BILLING_CURRENCY` | no | `USD` | Fallback currency label for products without one. |
| `PUBLIC_APP_URL` | no | — | Public base URL of this app (used for return links). |
| `PAYRAM_BASE_URL` | when enabled | — | PayRam site URL, e.g. `https://pay.example.com`. |
| `PAYRAM_API_KEY` | when enabled | — | Project API key from the PayRam dashboard. |
| `PAYRAM_WEBHOOK_SECRET` | no | = API key | HMAC key for webhook signatures. PayRam signs with the project API key by default. |
| `PAYRAM_TIMEOUT` | no | `15` | Seconds for provider HTTP calls. |
| `BILLING_CHECKOUT_TTL_SECONDS` | no | `86400` | Checkout link lifetime (PayRam default is 24h). |
| `BILLING_MAX_OPEN_INVOICES` | no | `5` | Abusive-checkout guard per gym. |
| `PB_ADMIN_EMAIL` | yes (when billing on) | — | PocketBase superuser for billing data access. |
| `PB_ADMIN_PASSWORD` | yes (when billing on) | — | PocketBase superuser password. |

If `BILLING_ENABLED=true` without PayRam credentials, startup **fails fast**
(`RuntimeError`) rather than silently degrading. Missing `PB_ADMIN_*` surfaces
as a clear error on the first billing operation.

---

## 5. PayRam setup

1. Deploy/point at a PayRam server; note its **Site URL** → `PAYRAM_BASE_URL`.
2. In the PayRam dashboard create a project/API key → `PAYRAM_API_KEY`.
3. **Settings → Webhook → Add Endpoint**: `https://<your-app-domain>/webhooks/payram`,
   mark it **active**.
4. Ensure the app is reachable over public **HTTPS** (PayRam requires HTTPS).
5. Set `PB_ADMIN_EMAIL` / `PB_ADMIN_PASSWORD` to a PocketBase superuser.
6. Create at least one active row in `billing_products` (the migration seeds
   `seats-10` and `seats-30`; edit prices/seats in the admin UI — no code change).
7. Restart the app.

### PayRam contract used (verified against docs.payram.com)

- Create: `POST {BASE_URL}/api/v1/payment` with header `API-Key`, body
  `{customerEmail, customerID, amountInUSD, invoiceID, expire?, currency?}` →
  `{reference_id, url, host}`.
- Status: `GET {BASE_URL}/api/v1/payment/reference/{reference_id}` →
  `{paymentState, amountInUSD, filled_amount_in_usd, ...}`.
- Webhook: `POST` JSON; verify `X-Payram-Signature: sha256=<hex>` =
  `HMAC-SHA256(raw_body, PAYRAM_API_KEY)`; legacy verbatim `API-KEY` accepted.
- States: `OPEN`, `PARTIALLY_FILLED`, `FILLED`, `OVER_FILLED`, `CANCELLED`.

### Test payment workflow

PayRam is a real self-hosted crypto server; use its **testnet** deployment for a
full flow. There is no "test card". Steps: buy a pack from `/billing` → pay the
PayRam page → webhook fires → seats increase. To exercise without a real chain,
`pytest` covers the whole path with a mocked provider (§8).

---

## 6. User experience

- `GET /billing` (owner only): KPI strip (in use / capacity / available),
  seat packs with server-side prices, and the gym's payment history.
- `POST /billing/checkout` (`product_key`): creates the invoice + provider
  checkout, then `HX-Redirect` to the **validated** provider URL.
- `GET /billing/return?invoice=…`: reconciles with the provider, shows
  pending/paid/failed honestly; polls `/billing/checkout/{ref}/status` every 5s
  until settled, then stops.
- Paywall: registering a trainee past capacity returns **409** with an
  out-of-band banner linking to `/billing`; the form is preserved.
- `POST /billing/invoices/{ref}/refund` (owner): records a manual refund.

The return page **never** grants seats from a URL parameter — only a verified
provider state does.

---

## 7. Security & reliability

- **Pricing**: amount and seat count come from the product record; the client
  sends only a product key.
- **Checkout URL**: redirect is refused unless the URL host equals the PayRam
  host (open-redirect guard, unit-tested).
- **Webhook auth**: HMAC-SHA256 over the exact raw body, constant-time compare;
  rejected before any DB access. Never disabled.
- **Idempotency**: `billing_events.dedup_key` (unique) stops duplicate
  deliveries; `credit_transactions.idempotency_key` (unique) makes fulfillment
  exactly-once even across restarts. Verified against the provider's status
  endpoint before granting.
- **Partial/over payment**: only `FILLED`/`OVER_FILLED` grant seats; a partial
  payment grants nothing.
- **No downgrade**: a settled invoice is never returned to a pending state.
- **Concurrency**: seat-granting runs under a per-tenant in-process lock
  (`ponytail:` documented — correct for the single-container deployment; a
  multi-instance deploy needs a DB-level guarantee).
- **Secrets**: never logged, never rendered, never in the JS bundle (tested).
- **Recovery**: unknown-invoice webhooks are durably recorded (not lost);
  `reconcile_tenant` re-checks unsettled invoices on the return page.

---

## 8. Tests

`tests/test_billing.py` (38 billing tests; 93 in the full suite, all passing):

- Provider status mapping; entitlement only for paid states.
- Checkout-URL trust guard; signature valid/invalid/legacy/missing; webhook
  parse + dedup key; malformed bodies rejected.
- Config: disabled default, fail-fast when enabled without credentials,
  integer parsing.
- Checkout: server-side price, provider failure → invoice `failed`, inactive
  product rejected, open-invoice limit.
- Webhook: fulfill once + dedup, invalid signature → 401, unknown invoice not
  fulfilled, partial payment grants nothing, late event cannot downgrade.
- Refund: compensating entry; unpaid rejected.
- Seats: capacity math, at-capacity gate, ledger sum.
- End-to-end over HTTP: unsigned → 401, valid signature → 200, oversized → 413.
- Template rendering of all three billing components.
- Static contracts: webhook public + CSRF-exempt, trainee create guarded,
  billing routes owner-only, all billing rules `null`, no API key in the bundle.

**Not verified here** (no live PocketBase / PayRam): actual migration execution,
real collection-rule enforcement by PocketBase, and a real crypto payment.

---

## 8a. Live verification (against `db.gyme.cloud` + `pay.rastin.cloud`)

Verified on a real deployment (PocketBase, PocketBase superuser, PayRam v3.8.2):

| Check | Result |
| --- | --- |
| Billing collections created with all rules `null` | ✅ |
| Anonymous read of `billing_products` | ✅ blocked (403) |
| Unique idempotency index (`credit_transactions`) | ✅ duplicate rejected (400) — exactly-once is DB-enforced |
| Products read from live DB | ✅ `seats-10` ($29), `seats-30` ($69) |
| Seat summary from live data | ✅ capacity 5, used 1, remaining 4 |
| Webhook signature with the real PayRam API key | ✅ valid accepted, forged rejected |
| Full fulfillment cycle | ✅ capacity 5 → 15, invoice `paid` |
| Re-applying the same payment | ✅ capacity stays 15 (no double grant) |
| Checkout when PayRam is unhealthy | ✅ fails gracefully, invoice marked `failed`, user-safe message |

### PayRam connection — verified live

Verified against `pay.rastin.cloud` (PayRam **v3.8.2**):

| Check | Result |
| --- | --- |
| API key accepted | ✅ (wrong/missing → `401 UNAUTHORIZED`) |
| `POST /api/v1/payment` | ✅ returns `reference_id` + checkout `url` |
| `GET /api/v1/payment/reference/{ref}` | ✅ returns `paymentState` |
| App `create_checkout` → real PayRam reference | ✅ invoice persisted `awaiting` |
| App `reconcile_invoice` → real status | ✅ `OPEN` → `awaiting`, capacity unchanged |
| Signed webhook delivery | ✅ `200`, matched, recorded once |
| Duplicate webhook delivery | ✅ `200 duplicate:true`, one event row |
| Unsigned webhook | ✅ `401`, rejected before any DB access |

> **Gotcha found live:** PayRam's `currency` request field is a **crypto token**
> restriction (`USDC`, `USDT`, …). Sending a fiat code (`USD`) makes PayRam
> return `500`. Gyme amounts are always USD and the customer may pay in any
> supported crypto, so the adapter **does not send `currency`**. The product's
> `currency` column is a display label only.

> **Health note:** `GET /api/v1/health` still reports
> `"redis-server":"FATAL"` while all other workers are `RUNNING`. Payment
> creation and status lookups nonetheless succeed; treat a `FATAL` worker as
> worth a `--restart` if creation ever starts failing:
> `bash <(curl -fsSL https://payram.com/setup_payram.sh) --restart`.

> **Still requires a real payment to confirm end-to-end:** seat grant on an
> actual on-chain `FILLED` webhook. The full plumbing (signature, idempotency,
> ledger, reconciliation) is verified; only the funded deposit is not.

---

## 9. Extending

- **New provider** (e.g. Stripe): implement `PaymentProvider` in a new module;
  switch in `get_provider()`. Accounting, seats, and UI are unchanged.
- **Subscriptions**: PayRam cannot auto-charge. If needed, add a
  `subscriptions` collection and an operator-confirmed renewal that appends a
  ledger grant; do not fake recurring charges.
- **Other metered features**: add a cost table and reuse the ledger; the seat
  model is deliberately narrow.

---

## 10. Operations & troubleshooting

| Symptom | Cause | Action |
| --- | --- | --- |
| `/billing` shows "provider not configured" | `PAYRAM_BASE_URL`/`PAYRAM_API_KEY` missing | set them, restart |
| Startup `RuntimeError` about PayRam | `BILLING_ENABLED=true` without creds | set creds or disable billing |
| Webhook returns 401 | wrong `PAYRAM_WEBHOOK_SECRET`/key, or forged request | match the dashboard API key |
| Payment paid but no seats | webhook not delivered | open `/billing/return?invoice=…` (reconciles) or re-check `billing_events` |
| `PB_ADMIN_*` error on billing | superuser env missing | set `PB_ADMIN_EMAIL`/`PB_ADMIN_PASSWORD` |
| "too many unpaid invoices" | open-invoice limit | complete or wait for expiry |

**Investigating a payment:** look up `billing_invoices` by `invoice_ref`; check
`billing_events` for `reference_id`; confirm `paymentState` via
`GET /api/v1/payment/reference/{ref}`. Fulfillment is recorded in
`credit_transactions` (`grant:<invoice_ref>`).

**Rotating credentials:** update `PAYRAM_API_KEY` (and webhook secret if used)
and restart; update the PayRam webhook endpoint if the key changed. Rotate
`PB_ADMIN_PASSWORD` and restart.

**Refunds:** PayRam has no automated crypto refund API. Confirm the refund
out-of-band, then `POST /billing/invoices/{ref}/refund` (owner) or via the admin
UI — this reverses the seat grant with a compensating ledger row. History is
never edited.
