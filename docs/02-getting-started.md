# 02 — Getting Started (Development)

Gyme's browser UI is a SvelteKit/Svelte 5 app in `frontend/`; FastAPI in `app/`
provides the JSON API, and PocketBase is an external dependency.

## Prerequisites

- Python 3.11+
- Node.js 22+ and npm
- A reachable PocketBase instance with the collections and tenant record described
  in [configuration & deployment](06-configuration-deployment.md)

## Install

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r app/requirements.txt
npm --prefix frontend ci
```

## Configure and run

Set the PocketBase URL and the FastAPI origin used by the SvelteKit server:

```bash
export PB_URL="http://127.0.0.1:8090"
export BACKEND_URL="http://127.0.0.1:8000"
```

In separate terminals, run:

```bash
uvicorn app.main:app --reload --port 8000
```

```bash
npm --prefix frontend run dev
```

The frontend listens on port 5173. Tenant lookup uses the browser's hostname,
which must match a `domain` in PocketBase's `tenants` collection. For local
development, map a tenant hostname to loopback (for example,
`127.0.0.1 yourgym.local` in `/etc/hosts`) and open
`http://yourgym.local:5173`.

The browser sends page requests to SvelteKit. SvelteKit SSR/load functions and
form actions call FastAPI through the same-origin `/api/v1` proxy; the browser
does not call PocketBase directly. Set `BACKEND_URL` to the reachable FastAPI
origin. The backend trusts forwarded host/protocol/client-IP headers only from
the configured proxy peer; local direct development defaults to loopback trust.

## Configuration notes

| Variable | Development default | Meaning |
| --- | --- | --- |
| `PB_URL` | `http://127.0.0.1:8090` | PocketBase base URL. Required when `ENV=production`. |
| `ENV` | `dev` | `production` disables Swagger and debug routes and enables production logging/security behavior. |
| `ALLOWED_HOSTS` | unset | Optional comma-separated FastAPI host allowlist. |
| `TRUSTED_PROXIES` | `127.0.0.1,::1` | Immediate peer addresses/CIDRs allowed to supply forwarded headers. The production container needs no override: the in-container SvelteKit BFF is the loopback peer. |
| `BACKEND_URL` | `http://127.0.0.1:8000` | FastAPI origin for SvelteKit; the production image sets the same loopback address. |

`.env` files are not loaded automatically; export variables or configure the
process environment.

## Checks and localization

```bash
npm --prefix frontend run check
npm --prefix frontend run build
.venv/bin/python -m pytest -q
ruff check .
black --check .
```

Svelte UI dictionaries are in `frontend/src/lib/i18n.ts`. FastAPI/PWA messages
use gettext catalogs in `app/locales/`; the Make targets update those catalogs
only (`make i18n-extract`, `make i18n-update`, `make i18n-compile`).

In non-production mode, FastAPI serves Swagger UI at `/docs` and OpenAPI JSON at
`/openapi.json` on port 8000. `/healthz` is a PocketBase-independent liveness
check. See [troubleshooting](07-troubleshooting-known-issues.md) for common
setup issues.
