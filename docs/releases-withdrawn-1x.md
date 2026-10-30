# Withdrawn 1.x releases (archive)

The project is pre-1.0. On 2026-10-30 the `v1.0.0`–`v1.7.0` release identifiers
were withdrawn as a numbering error: the application never left the 0.x line,
and the `v1.5.0`/`v1.6.0` billing experiment had already been reverted on `main`.
The commits themselves are untouched and still reachable; only the tags and
GitHub releases were removed. The line resumes at `v0.10.0`.

This file preserves the release notes that were published under those tags so
the record is not lost. Container images published for them may still be
pullable from GHCR, but they are unsupported and will not be rebuilt.

## v1.4.0 — 2026-09-28 — commit `439e85f`

**v1.4.0 — persistent shell, Slate Pine theme**

## Persistent shell navigation

The app shell now stays mounted. Dock taps and post-action redirects swap only `#page-content` instead of reloading the page, so the header, bottom dock, modal host, and toast renderer survive every navigation. Browser back/forward work through real pushed URLs, and the header title plus active dock item resync after each swap.

The global `hx-boost` is off deliberately; boosting was the source of the full-page flashes.

## Slate Pine theme

The palette moves from Caldera Evolved to Slate Pine: deep slate surfaces, pine accents, a single ember reserved for destructive actions. The DaisyUI custom theme is now registered under its real name instead of being defined but never applied, which is why the theme tokens previously had no effect.

## Fixed 1140px shell with desktop sidebar

The content column is capped at a fixed 1140px and gains a persistent sidebar on desktop, replacing the bottom-only dock for coach and owner roles. The dock remains for the narrow/mobile layout.

## Typography

Inter for the interface, DM Sans for display headings, loaded through the same preconnect and stylesheet links as before.

## Granular HTMX behavior

- Owner dashboard timeframe filter returns the content partial even when HTMX sends the target with a leading hash
- Marking a plan day done confirms with a toast instead of `HX-Refresh`, so the shell is no longer torn down mid-interaction
- Forms carry `hx-disabled-elt` and `hx-sync` so a slow request cannot be double-submitted and input state is not clobbered
- List and search inputs keep the current row visible while a request is in flight

## Layout and viewport fixes

- Trainee dashboard reflowed so the done button and progress fit without horizontal scroll on small screens
- Progress log form no longer overflows its card
- Search results and table rows keep readable spacing after partial swaps

## Upgrading

`APP_VERSION` moved to `1.4.0`. That value drives the service worker cache name and the static asset cache-busting query strings, so the new shell and theme take effect on first load without a manual cache clear.


## v1.5.0 — 2026-10-13 — commit `a73d814`

**v1.5.0 — seat billing & PayRam**

## Seat billing & PayRam

Gyme can now charge gyms for **active trainee seats**. Every gym gets a free
allowance (`BILLING_FREE_SEATS`, default 5); owners buy one-time seat packs that
add permanent capacity, paid in crypto through a self-hosted **PayRam** server.

### Added
- **Billing service** (`app/services/billing/`) behind a provider-agnostic
  `PaymentProvider` contract, with a PayRam adapter as the only provider code.
- **Owner Billing screen** — usage (in use / capacity / available), seat packs
  with server-side prices, payment history, and a checkout return page that
  polls until the payment settles.
- **Server-side enforcement** — trainee creation is blocked at capacity (HTTP
  409) under a per-tenant lock; the form shows a paywall banner.
- **Signature-verified webhook** (`POST /webhooks/payram`, public + CSRF-exempt)
  that grants seats exactly once, with durable dedup and forward-only status.
- **Admin-only PocketBase schema** shipped as
  `pb_migrations/1750000000_billing.js` (all rules closed).
- **38 billing tests**; suite now 93 tests.

### Fixed
- Coach and trainee edit forms used Django `{% include ... with %}` syntax,
  which is invalid Jinja2 and raised `TemplateSyntaxError` when pre-filling a
  phone number.
- Missing default app icons under `app/static/icons/` (favicon, PWA icons)
  that `app/routes/pwa.py` already referenced, and the login page icon path.

### Docs
- New [docs/billing.md](https://github.com/Rastin-Amani/Gyme/blob/v1.5.0/docs/billing.md):
  architecture, schema, configuration, PayRam setup, security, operations.
- Refreshed API reference, configuration/deployment, overview and README.

### Configuration
Billing is **off by default**. Enabling it requires `BILLING_ENABLED=true`,
`PAYRAM_BASE_URL`, `PAYRAM_API_KEY` and `PB_ADMIN_EMAIL`/`PB_ADMIN_PASSWORD`.

**Full changelog:** https://github.com/Rastin-Amani/Gyme/compare/v1.4.0...v1.5.0

## v1.6.0 — 2026-10-13 — commit `ea583af`

**v1.6.0 — billing hardening**

## Billing hardening

Follow-up to the seat-billing release: billing is now safely vendor-optional and
easily switched off, and the PocketBase schema bug that could `500` the Billing
page is fixed.

### Changed
- **Graceful degradation.** Billing never `500`s a normal page. Missing
  `PB_ADMIN_*` or invalid config makes the feature report itself unavailable —
  `/billing` renders a "not configured" notice, checkout/refund/webhook return
  `503`, and trainee creation logs the error and proceeds (fails open).
- **`BILLING_ENABLED=false` removes the feature entirely:** the Billing nav link
  disappears from the sidebar and dock, `GET /billing`, checkout, return, status,
  refund and `POST /webhooks/payram` all return `404`, trainee creation is not
  seat-limited, and no billing PocketBase access happens at all. Re-enabling is a
  one-variable change.

### Fixed
- Billing collections now define the `created`/`updated` autodate fields.
  PocketBase does not add them for API-created collections, so `sort=-created`
  returned `400` and `/billing` failed.
- `list_invoices` fails soft instead of propagating a query error to the page.
- Trainee creation no longer breaks when the billing seat check errors.

### Docs & tests
- Docs aligned with degraded/disabled behavior, including the operator
  troubleshooting table.
- Suite grew to **107 tests** (52 billing).

**Full changelog:** https://github.com/Rastin-Amani/Gyme/compare/v1.5.0...v1.6.0

## v1.7.0 — 2026-10-30 — commit `bfa2d5d`

**v1.7.0 — DaisyUI interface rebuild & request-path speed**

## Interface rebuild

The whole interface now comes from **one DaisyUI theme** instead of a custom
component layer. Same product, rebuilt on stock components:

- persistent shell: translucent sticky header, sidebar menu on desktop, mobile
  dock, and a single `#page-content` region that HTMX swaps
- ledgers (`list`/`list-row`), `stats` strips and `tabs-box` rails replace the
  bespoke `ledger-row`, `kpi-strip`, `side-nav` and Today rail
- every form, modal and dialog rebuilt on `fieldset` / `label.input` /
  `modal-box`, with native validation and 45px controls
- no webfont request; hierarchy comes from the system stack
- new Slate Pine tokens: paper canvas, pine as the only actionable colour,
  flat by contract (`--depth: 0`)

## Speed

- **One connection pool.** PocketBase calls reuse a shared httpx pool instead of
  rebuilding a client (TLS handshake) per request.
- **Cached token verification.** A verified `pb_auth` token is trusted for 30 s
  per process, so navigation no longer pays a round-trip before the handler
  runs. Revocation and password changes take effect within 30 s.
- **Parallel reads.** Independent PocketBase queries on the dashboard, coach
  table and trainee plans run concurrently (bounded at 8).
- **Compression + asset caching.** Responses are gzipped; `/static/*` is served
  `immutable` for a year and cache-busted by a build-derived `ASSET_VERSION`, so
  stale CSS/JS can no longer be served after a deploy.

## Fixes

- service-worker cache version follows the built assets, not a hand-bumped
  constant
- PWA manifest uses the current theme colours, and its icon URLs are versioned
  so replacing artwork is no longer stuck behind a one-year cache
- favicon link no longer costs a redirect hop per load

## Breaking

- **Billing (added in v1.5.0/v1.6.0) is not part of this release.** `main`
  rolled the billing feature back before this work, so this line continues from
  the pre-billing code with the rebuilt interface. Deployments that rely on
  seat entitlements or PayRam checkout should stay on `v1.6.0`.

## Verification

- `pytest -q` → 57 passed
- `ruff check .` clean · `black --check .` clean
- booted the app against a live PocketBase: `/login` renders, `/healthz` 200,
  `/manifest.json` and `/sw.js` carry the build version, `/static/app.css`
  returns `Cache-Control: immutable`, HTML is gzipped

Full diff: https://github.com/Rastin-Amani/Gyme/compare/v1.6.0...v1.7.0


