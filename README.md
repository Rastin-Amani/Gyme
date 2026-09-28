# Gyme

[![CI](https://img.shields.io/github/actions/workflow/status/Rastin-Amani/Gyme/ci.yml?branch=main&label=CI&logo=github)](https://github.com/Rastin-Amani/Gyme/actions)
[![License: ISC](https://img.shields.io/github/license/Rastin-Amani/Gyme)](LICENSE)
[![Release](https://img.shields.io/github/v/release/Rastin-Amani/Gyme)](https://github.com/Rastin-Amani/Gyme/releases)
[![Docker (GHCR)](https://img.shields.io/badge/Docker-GHCR-2496ED?logo=docker&logoColor=white)](https://github.com/Rastin-Amani/pkgs/container/gyme)

**Gyme** is a multi-tenant gym coaching platform: each gym gets its own branded,
installable web app (PWA) where owners and coaches manage trainees and deliver
training, nutrition, and supplement plans — and trainees follow their daily plan
from their phone. The UI is multilingual with **English as the default language**;
Spanish, Turkish, and Armenian are also supported.

- **Status:** actively developed; backend and frontend checks live under
  `tests/` and `frontend/`.
- **Links:** [Releases](https://github.com/Rastin-Amani/Gyme/releases) · [Discussion](https://github.com/Rastin-Amani/Gyme/discussions) · [Security policy](SECURITY.md) · [Contributing](CONTRIBUTING.md)

---

## How it works in one paragraph

Every request is resolved to a **gym (tenant)** by the hostname the visitor uses.
The tenant's members log in with an email/password managed by the gym:

- **Owners** see gym-wide stats, manage **coaches** and **trainees**, build
  **plans** (training / diet / steroid) from reusable **templates**, and record
  body-metric assessments (**progress logs**) with photos.
- **Trainees** get a personal "Today" dashboard that shows today's slice of each
  plan and a big **Done** button that advances them to the next day.

SvelteKit renders the application with SSR and client-side navigation. FastAPI
remains the same-origin JSON/API backend, with PocketBase handling records,
auth tokens, and file storage. The app remains installable as a PWA with
per-gym branding, icon/favicon, offline caching, and an offline fallback page.

## Key capabilities

| Area | What it does |
| --- | --- |
| Multi-tenancy | Hostname-based tenant resolution, per-tenant name/logo/manifest |
| Roles | `owner`, `coach` (scoped to own trainees/plans), `trainee` |
| Trainee management | List/search/filter, profile with health data, create/edit/delete |
| Plans & items | Training, diet, steroid plan types with type-specific items |
| Plan templates | Save reusable templates, apply one to a trainee (copies all items) |
| Progress logs | Body metrics (BMI/BFP/BMR/TDEE/LBM/WHR) + up to 5 photos; submitted metric ranges are validated by the API |
| Owner dashboard | Trainee/plan counters and per-coach stats with week/month/all timeframes |
| PWA | Dynamic manifest per gym, service worker caching, offline page and connectivity banner |

## Quick start (development)

Prerequisites: Python 3.11+, Node.js 22+, and a running PocketBase instance.

```bash
# 1. Python environment
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r app/requirements.txt

# 2. Frontend tooling (SvelteKit)
cd frontend && npm ci && cd ..

# 3. Point both servers at PocketBase and each other
export PB_URL="http://127.0.0.1:8090"
export BACKEND_URL="http://127.0.0.1:8000"

```

In separate terminals, run the backend and frontend:

```bash
uvicorn app.main:app --reload --port 8000
```

```bash
npm --prefix frontend run dev
```

Open the app on a hostname that matches a `domain` value of a record in your
PocketBase `tenants` collection (for example, add `yourgym.localhost` as a
tenant domain and open `http://yourgym.localhost:5173`). SvelteKit serves the
browser UI; FastAPI stays on port 8000 for the private API hop. See
[docs/02-getting-started.md](docs/02-getting-started.md) for the full walkthrough.

### Environment variables

| Variable | Default | Purpose |
| --- | --- | --- |
| `PB_URL` | `http://127.0.0.1:8090` in development; required in production | Base URL of the PocketBase instance |
| `ENV` | `dev` | Set to `production` to disable Swagger docs and `/debug/*` routes and switch logs to JSON |
| `ALLOWED_HOSTS` | *(unset)* | Optional comma-separated allowlist passed to Starlette `TrustedHostMiddleware`; in production a warning is logged when it is unset |
| `BACKEND_URL` | `http://127.0.0.1:8000` | FastAPI origin used by the SvelteKit same-origin API proxy (the production image sets the internal loopback address; use `http://127.0.0.1:8000` for local development) |

> Note: `python-dotenv` is listed in requirements but never invoked — `.env`
> files are **not** loaded automatically; export variables in the shell.

## Development

Run the backend and frontend in separate terminals:

```bash
uvicorn app.main:app --reload --port 8000
```

```bash
npm --prefix frontend run dev
```

Then run checks as needed:

```bash
ruff check .                    # lint
black .                         # format
```

Swagger UI is available directly on the development backend at
`http://127.0.0.1:8000/docs` and the OpenAPI schema at
`http://127.0.0.1:8000/openapi.json` while `ENV` is not `production`. Read-only
debug endpoints live under `/debug/*` in dev only.

## Architecture overview

```
Browser (SvelteKit SSR + client navigation)
   │  same-origin HTML + /api/v1 JSON
   ▼
SvelteKit Node server (frontend/)
   ├── SSR page loads/actions + components
   └── /api/v1 proxy ── forwards cookies + trusted tenant host to FastAPI
   ▼
FastAPI (app/main.py)
    ├── TenantMiddleware ── resolves tenant + validates pb_auth cookie
    ├── JSON API (app/routes/api.py)   HTTP/auth boundary
    └── Services (app/services/**)    PocketBase queries & business rules
   ▼
PocketBase (external)  ── collections: tenants, users, trainees, plans,
                          training_items, diet_items, steroid_items,
                          progress_logs, plan_progress, leads
                          (leads is written by the separate marketing app)
                          + auth tokens + file storage (logos, progress photos)
```

Deeper material: [docs/04-architecture.md](docs/04-architecture.md),
[docs/05-api-reference.md](docs/05-api-reference.md).

## Project structure

```
frontend/
├── src/routes/         # SvelteKit pages, SSR loads and form actions
├── src/lib/            # UI, API client, i18n and server helpers
├── src/service-worker.ts
└── package.json        # SvelteKit + adapter-node
app/
├── main.py            # FastAPI app assembly and docs gating
├── middleware.py      # TenantMiddleware (tenancy + auth + request logging)
├── pb.py              # PocketBase client factory (PB_URL)
├── logging_config.py  # structlog setup (console dev / JSON prod)
├── routes/            # JSON API, PWA and dev-only diagnostics
├── services/          # PocketBase access & business logic
└── static/swagger/    # development API docs assets
data/                  # bundled exercise and food CSV datasets
Dockerfile             # single production image: SvelteKit + FastAPI
docker-entrypoint.sh   # runs both services; exits if either one dies
```

## Documentation

| Document | Audience |
| --- | --- |
| [Product overview](docs/01-overview.md) | Everyone — what Gyme is and what it does |
| [Getting started](docs/02-getting-started.md) | Developers setting up a dev environment |
| [Architecture](docs/04-architecture.md) | Technical deep dive |
| [API reference](docs/05-api-reference.md) | All HTTP routes |
| [Configuration & deployment](docs/06-configuration-deployment.md) | Operators |
| [Troubleshooting & known issues](docs/07-troubleshooting-known-issues.md) | Everyone |

## Known limitations

Documented in detail in
[docs/07-troubleshooting-known-issues.md](docs/07-troubleshooting-known-issues.md).
Highlights:

- Accounts created in-app get a **random 15-character password** that the UI
  never displays — staff must share or reset it before the new user can log in.
- Login attempts are rate-limited; password changes have separate validation
  and are not covered by that login rate limit.
- CI runs Python lint/format/tests; frontend checks and production builds use
  the SvelteKit package under `frontend/`.

## Deployment

The root `Dockerfile` builds one production container: the SvelteKit SSR
server (public port **3000**) and the FastAPI backend (loopback-only port
8000, unreachable from outside the container) run together, supervised by
`docker-entrypoint.sh`, which exits the container if either service stops.
No Compose file is involved. Set `PB_URL` and `ALLOWED_HOSTS` at runtime;
PocketBase remains external.

```bash
PB_URL="https://your-pocketbase.example" \
ALLOWED_HOSTS="gym.example.com" \
  docker build -t gyme . && docker run -p 3000:3000 gyme
```

The GitHub workflow publishes this same image to **GHCR** on pushes to `main`
(tag `latest`) and version tags.

For Dokploy, create a **Dockerfile** application pointing at this repository
and expose port 3000; see
[docs/06-configuration-deployment.md](docs/06-configuration-deployment.md) for
the exact settings. The public hostname must match a `tenants` record.

## Contributing

Contributions are welcome — see [CONTRIBUTING.md](CONTRIBUTING.md) for setup,
code conventions and the PR checklist (`make test`, `ruff check .`, `black .`,
`npm --prefix frontend run check`).


## Internationalization (i18n)

Languages (cookie-based): **en** (default, LTR, source msgids), **es**, **tr**, **hy**.

- The locale switcher stores the selected language in the `gyme_locale` cookie;
  every supported locale is LTR.
- Svelte UI strings live in `frontend/src/lib/i18n.ts`. FastAPI/PWA messages use
  gettext catalogs under `app/locales/`.

```bash
make i18n-extract   # refresh messages.pot
make i18n-add LOCALE=de   # add a backend gettext catalog
make i18n-update    # merge new msgids into existing .po files
make i18n-compile   # build .mo
```

To add a language, update both the frontend dictionary and backend locale
registry/catalogs; the gettext Make targets do not generate Svelte translations.
