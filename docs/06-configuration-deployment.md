# 06 — Configuration & Deployment

**Verification status:** based on `app/pb.py`, `app/main.py`,
`logging_config.py`, `Dockerfile`, `.dockerignore`, `.gitignore`,
`vite.config.js`, and the service-layer query code in the current repo.
PocketBase-side settings (API rules, SMTP, backups) are instance
configuration — not stored here — and are marked accordingly.

---

## Part 1 — Configuration reference

### Environment variables

| Variable | Required | Default | Effect |
| --- | --- | --- | --- |
| `PB_URL` | effectively yes | `http://db.dev.gyme.cloud` | Base URL of the PocketBase instance used for **all** data access (`app/pb.py`). ⚠️ The default is the project's shared **dev** database over plain HTTP; any deployment that forgets this variable silently reads/writes that server |
| `ENV` | no | `dev` | Any value other than exactly `production` behaves as dev. In production mode: Swagger docs + `/openapi.json` disabled, `/debug/*` router excluded (and its routes cleared defensively), structlog switches to JSON output |
| `ALLOWED_HOSTS` | no | unset | When set (comma-separated), adds FastAPI's `TrustedHostMiddleware` with those hosts plus `localhost`/`127.0.0.1`/`testserver` in dev. In production without it, a warning is logged and no host validation is applied |

> **Important:** `python-dotenv` appears in `requirements.txt`, but nothing
> ever calls it. `.env` files are **not** loaded. Provide variables through the
> shell, container environment, or process manager.

Ports come from uvicorn/Docker invocation, and branding lives in PocketBase
data (below). Host allow-listing is the only optional runtime knob beyond the
table above.

### Tenant (gym) record fields

The `tenants` collection drives per-domain behavior and all branding:

| Field | Used by | Meaning |
| --- | --- | --- |
| `domain` | middleware | Exact hostname (without port) that maps requests to this gym. One record per served hostname |
| `name` | header, login card, manifest | Display name ("Gym" fallback in UI) |
| `logo` (file) | login, dashboard header, favicon redirect, manifest icons, iOS splash | Served via PocketBase thumbnails (`?thumb=…`) |
| `theme` | `base.html` `data-theme` | daisyUI theme name: default `gyme`; `custom` enables CSS-variable injection; `light` also supported |
| `brand_theme` | `base.html` `<style>` block when `theme == "custom"` | Map of CSS variable names → values (`_` rendered as `-`) |
| `primary_color`, `brand_colors.base_100`, `brand_colors.base_content` | iOS splash generator | Splash background/text colors with sensible fallbacks |
| `is_main` | (no longer read by the app) | Previously flagged the tenant serving the marketing landing page; the app now always redirects `/` → app and hosts no landing page |

### PocketBase collections required

Create these before first use (field types follow how the code reads/writes
them; exact PB field options — e.g. relation vs text ids — are your choice as
long as filters like `tenant="..."` work):

| Collection | Fields referenced by code |
| --- | --- |
| `users` (auth) | `first_name`, `last_name`, `phone`, `tenant`, `role` (`owner`\|`coach`\|`trainee`), `emailVisibility` (+ standard email/password) |
| `tenants` | see table above |
| `trainees` | `user` (→users), `tenant`, `status`, `gender`, `birthdate`, `blood_type`, `height`, `weight`, `training_history`, `steroid_history`, `supplement_history`, `limitations`, `notes` |
| `plans` | `tenant`, `type`, `trainee`, `coach`, `start_date`, `end_date`, `days_per_week`, `status`, `notes`, `is_template` (bool), `template_name` |
| `training_items` | `tenant`, `plan`, `name`, `category`, `seq`, `order`, `sets`, `reps`, `weight`, `rest_seconds`, `notes` |
| `diet_items` | `tenant`, `plan`, `meal_name`, `name`, `quantity`, `seq`, `order`, `notes` |
| `steroid_items` | `tenant`, `plan`, `name`, `type`, `dosage`, `frequency`, `seq`, `order`, `notes` |
| `progress_logs` | `tenant`, `trainee`, metric numbers (`height weight chest waist hip arms bmi bfp bmr tdee lbm whr`), `notes`, `progress_photos` (multiple files, ≤5) |
| `plan_progress` | `tenant`, `plan`, `current_seq` |
| `leads` | `name`, `phone`, `position`, `coaches_count`, `trainees_count`, `gym_name`, `note` | written only by the **separate marketing application**; this app no longer writes or reads leads |

Operational notes:

- The app authenticates end users against `users` and then performs all reads/
  writes with that user's token. **Unverified / your responsibility:** API
  rules must allow each role's expected operations (e.g. staff creating users,
  reading tenants). The repo contains no rule definitions or migrations.
- There is no seed script. Minimum bootstrap = one `tenants` record matching a
  real hostname plus at least one owner account (create directly in PocketBase
  admin since the UI has no signup).
- File storage (tenant logos, progress photos) uses PocketBase file fields;
  size/type limits enforced app-side are 5 files × 5 MB, JPEG/PNG/WebP/GIF.

### Versioning

- `APP_VERSION` constant in `app/main.py` (currently `1.0.0`) drives:
  template footer/global, and the PWA cache version injected into `sw.js`
  (bumping it purges clients' caches on next visit).
- `app/version.text` mirrors it (`"1.0.0"`); both are in sync. `base.html`
  derives the SW cache-buster from `{{ app_version }}`, so no hardcoding is
  left (known issue #7 resolved in 0.9.1).

## Part 2 — Deployment guide

### What ships vs what you build

The Docker image contains **only** Python code, templates, static assets and
the two CSV datasets (`.dockerignore` excludes Node/Vite files entirely).
Therefore the Vite build products (`app/static/app.css`, `app/static/app.js`,
`assets/`) must exist **before** `docker build`. They are committed today, so
a checkout builds as-is; after any Tailwind-class/template change run:

```bash
npm ci && npm run build     # regenerates app/static/app.{css,js} + assets/
```

then commit the rebuilt assets (or add an asset-build step to your CI image
build).

### Docker

`Dockerfile` summary (verified):

```dockerfile
FROM python:3.11-slim
WORKDIR /code
COPY ./app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt   # uses Chabokan PyPI mirror comment
COPY ./app ./app
COPY ./data ./data
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000",
     "--proxy-headers", "--forwarded-allow-ips", "*"]
```

Build & run:

```bash
docker build -t gyme .
docker run -d --name gyme \
  -p 8000:8000 \
  -e PB_URL="https://your-pocketbase.example" \
  -e ENV=production \
  gyme
```

Notes:

- The container listens on **8000**; a PB-free liveness endpoint is available:
  `GET /healthz` returns `{"status": "ok"}` (served by middleware before any
  PocketBase call). Use it as the Docker/health-check probe.
- `--proxy-headers --forwarded-allow-ips "*"` means uvicorn trusts
  `X-Forwarded-*` headers from **any** upstream. Keep the container reachable
  only from your trusted reverse proxy/network.

### Reverse proxy requirements

1. **Preserve the `Host` header** (or forward the original host in a header
   your proxy layer restores before uvicorn). Tenancy resolution reads the
   Host header verbatim — a proxy that rewrites every vhost to
   `localhost:8000` will break tenant lookup entirely.
2. One proxied hostname per gym, each matching a `tenants.domain` record.
   The marketing site is a separate application and is not served by this app.
3. TLS termination at the proxy. See the cookie caveat below before relying on
   HTTPS-only session behavior.

### Production checklist

- [ ] `ENV=production` set (docs/debug off, JSON logs)
- [ ] `PB_URL` explicitly set to the production PocketBase over **HTTPS**
- [ ] Every served hostname has an up-to-date `tenants` record (`domain`,
      `name`, `logo`, theme fields)
- [ ] Owner accounts exist; new accounts' random initial passwords (never
      displayed by the UI) are shared or reset via PocketBase admin before
      first login
- [ ] PocketBase API rules reviewed for the nine collections the app now uses
      (see above; `leads` belongs to the separate marketing app)
- [ ] `ALLOWED_HOSTS` set so `TrustedHostMiddleware` rejects spoofed hosts
- [ ] Static assets rebuilt if templates changed since last commit
- [ ] `APP_VERSION` bumped for releases so PWA caches invalidate
- [ ] PocketBase backups scheduled (instance-level; not handled by this app)

### Known hardening gaps to address before exposing publicly

(Each is detailed with evidence in
[07-troubleshooting-known-issues.md](07-troubleshooting-known-issues.md)):

1. Default `PB_URL` points at a shared **dev** database over plain HTTP;
   deployments must explicitly override it in production.
2. `GET /dashboard/debug-coach-stats` is registered in production too
   (authenticated but exposes raw plan/progress counts).
3. Initial passwords are random but **never surfaced in the UI** — staff must
   reset/share them via PocketBase admin (operational gap, not a security hole).
4. Change-password endpoint has no rate limit (login does: 5 attempts / 5 min).

### Logging in production

structlog emits one JSON object per event to stdout (timestamps ISO/UTC),
including `req_id`, `tenant_id`, route lifecycle events
(`request.started/completed/error`), and domain events such as
`login_success` / `template.apply_failed`. Ship stdout to your log pipeline;
no file handling or rotation is configured in-app.

## Documentation status

- Last verified: 2026-09-25 against `main` (uncommitted working tree after the
  marketing-app extraction; version 0.9.1).
