# API Reference

Gyme's browser UI is the SvelteKit application. Its server-side loads and form
actions call FastAPI through the same-origin `/api/v1` proxy; browser code does
not call FastAPI or PocketBase directly. FastAPI remains authoritative for
validation, authentication, tenant isolation, permissions, and persistence.

## Authentication and request rules

- Authentication uses the `pb_auth` cookie. Login sets an HttpOnly,
  `SameSite=Lax` cookie; it is Secure in production. The PocketBase token is
  never included in JSON responses or exposed to browser JavaScript.
- Login accepts JSON `{ "identity": "…", "password": "…" }` (identity may be
  an email). Attempts are rate-limited per client IP, identity, and tenant (5
  attempts per 5 minutes).
- Login and authenticated mutating requests require same-origin context. The
  private SvelteKit proxy forwards the original origin context; requests without
  it are accepted only from the configured trusted proxy peer for `/api/v1`.
- Tenant context comes from the public hostname and is resolved by FastAPI.
  Forwarded host, protocol, and client-IP headers are trusted only from the
  exact frontend peer on the private Compose network. Never expose the backend
  port publicly or trust arbitrary forwarded headers.
- Success and failure responses use JSON and meaningful HTTP status codes.
  Common failures include 401 (not authenticated), 403 (not permitted/CSRF),
  404 (missing tenant or record), 409 (conflict), and 422 (invalid input).
  The exact response body is endpoint-specific; clients must not treat a
  non-2xx response as success.

## JSON API (`/api/v1`)

All methods below are on the private FastAPI service and are exposed to the
browser only through the SvelteKit same-origin proxy.

### Authentication, profile, and locale

| Method | Path | Purpose | Access |
| --- | --- | --- | --- |
| GET | `/auth/me` | Current authenticated user | Authenticated |
| POST | `/auth/login` | Authenticate and set `pb_auth` | Public; rate-limited |
| POST | `/auth/logout` | Clear the auth cookie (`204`) | Public/idempotent |
| POST | `/auth/change-password` | Change password and refresh session | Authenticated |
| PATCH | `/auth/profile` | Update current user's profile | Authenticated |
| GET | `/locale/{code}` | Set supported locale preference | Public |

Locale codes are `en`, `es`, `tr`, and `hy`. This API endpoint accepts only an
allowlisted code and returns the selected locale. The separate FastAPI
`/locale/{code}` browser route also accepts a redirect target and validates it.
Svelte UI text is translated separately in `frontend/src/lib/i18n.ts`.

### Dashboards

| Method | Path | Purpose | Access |
| --- | --- | --- | --- |
| GET | `/dashboard` | Owner/coach summary; supports `timeframe=all\|week\|month` | Owner/coach |
| GET | `/dashboard/coach-stats` | Per-coach dashboard statistics | Owner/coach |
| GET | `/user/dashboard` | Trainee's current plan items | Trainee |
| GET | `/user/plans` | Trainee's plans | Trainee |
| GET | `/user/plans/{plan_id}` | Trainee plan detail | Assigned trainee |
| POST | `/user/plans/{plan_id}/done` | Advance the plan's current day | Assigned trainee |

### Trainees and coaches

| Method | Path | Purpose | Access |
| --- | --- | --- | --- |
| GET, POST | `/trainees` | List/filter or create trainees | Owner/coach |
| GET, PATCH, DELETE | `/trainees/{trainee_id}` | Read, update, or delete a trainee | Owner/authorized coach |
| GET, POST | `/coaches` | List or create coaches | Owner |
| GET | `/coaches/{coach_id}` | Read a coach and their trainees | Owner or that coach |
| PATCH, DELETE | `/coaches/{coach_id}` | Update or delete a coach | Owner |

List endpoints accept their supported filtering and pagination as query
parameters. Record IDs are always revalidated against tenant and role scope;
client-supplied IDs are not authorization.

### Plans, templates, and items

| Method | Path | Purpose | Access |
| --- | --- | --- | --- |
| GET, POST | `/plans` | List/filter or create plans; `is_template=true` lists templates | Owner/coach |
| GET, PATCH, DELETE | `/plans/{plan_id}` | Read, update, or delete a plan | Owner/authorized coach |
| POST | `/templates/{template_id}/apply` | Copy a template and its items to a trainee | Owner/authorized coach |
| GET, POST | `/items` | List or create plan items | Owner/authorized coach |
| GET, PATCH, DELETE | `/items/{item_id}` | Read, update, or delete an item | Owner/authorized coach |

### Progress logs

| Method | Path | Purpose | Access |
| --- | --- | --- | --- |
| GET | `/progress-logs/{log_id}` | Read a progress log | Owner/authorized coach |
| POST | `/progress-logs` | Create a log, including supported photo uploads | Owner/authorized coach |
| PATCH | `/progress-logs/{log_id}` | Update a log | Owner/authorized coach |

## Health, docs, and tenant PWA endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/healthz` | Process liveness; does not contact PocketBase |
| GET | `/docs` | FastAPI Swagger UI in non-production |
| GET | `/openapi.json` | OpenAPI schema in non-production |
| GET | `/debug/*` | Development-only JSON diagnostics |
| GET | `/manifest.json` | Tenant-aware PWA manifest; proxied by SvelteKit |
| GET | `/favicon.ico` | Tenant logo favicon redirect; proxied by SvelteKit |

The public browser origin serves the SvelteKit versions of `/manifest.json` and
`/favicon.ico`. FastAPI also exposes those endpoints internally for the BFF.
The former FastAPI `/login`, `/dashboard`, HTML CRUD pages, `/sw.js`, and
`/offline/` endpoints have been removed; SvelteKit owns those UI routes and its
service worker/offline page.
