# Gyme

**Gyme** is a multi-tenant gym coaching platform: each gym gets its own branded,
installable web app (PWA) where owners and coaches manage trainees and deliver
training, nutrition, and supplement plans — and trainees follow their daily plan
from their phone. The UI is fully in Persian (RTL) with Jalali date support.

- **Current version:** 0.8.0 (`app/main.py` `APP_VERSION`)
- **Status:** actively developed; no automated test suite yet

---

## How it works in one paragraph

Every request is resolved to a **gym (tenant)** by the hostname the visitor uses.
The tenant's members log in with an email/password managed by the gym:

- **Owners** see gym-wide stats, manage **coaches** and **trainees**, build
  **plans** (training / diet / steroid) from reusable **templates**, and record
  body-metric assessments (**progress logs**) with photos.
- **Trainees** get a personal "Today" dashboard that shows today's slice of each
  plan and a big **"انجام شد"** (Done) button that advances them to the next day.

The server renders HTML (Jinja2 + Tailwind/daisyUI); interactivity comes from
HTMX partial swaps with toast notifications. All data lives in an external
[PocketBase](https://pocketbase.io) instance (records, auth tokens, file
storage). The app is installable as a PWA with per-gym branding, icon/favicon,
offline caching, and an offline fallback page.

## Key capabilities

| Area | What it does |
| --- | --- |
| Multi-tenancy | Hostname-based tenant resolution, per-tenant theme/logo/manifest |
| Roles | `owner`, `coach` (scoped to own trainees/plans), `trainee` |
| Trainee management | List/search/filter, profile with health data, create/edit/delete |
| Plans & items | Training, diet, steroid plan types with type-specific items |
| Plan templates | Save reusable templates, apply one to a trainee (copies all items) |
| Progress logs | Body metrics (BMI/BFP/BMR/TDEE/LBM/WHR auto-calculated) + up to 5 photos |
| Owner dashboard | Trainee/plan counters and per-coach stats with week/month/all timeframes |
| Marketing site | Landing page with lead-capture form on the main tenant domain |
| PWA | Dynamic manifest per gym, service worker caching, offline page/banner, iOS install flow |

## Quick start (development)

Prerequisites: Python 3.11+, Node.js, and a running PocketBase instance.

```bash
# 1. Python environment
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r app/requirements.txt

# 2. Frontend tooling (Vite + Tailwind)
npm install

# 3. Point the app at your PocketBase instance
export PB_URL="http://127.0.0.1:8090"    # default is a remote dev server!

# 4. Build static assets once (or run `npm run dev` for watch mode)
npm run build                       # outputs app/static/app.css + app.js

# 5. Run the app
uvicorn app.main:app --reload
```

Open the app on a hostname that matches a `domain` value of a record in your
PocketBase `tenants` collection (e.g. add `127.0.0.1 yourgym.local` to your
hosts file and browse `http://yourgym.local:8000`). See
[docs/02-getting-started.md](docs/02-getting-started.md) for the full walkthrough.

### Environment variables

| Variable | Default | Purpose |
| --- | --- | --- |
| `PB_URL` | `http://db.dev.gyme.cloud` | Base URL of the PocketBase instance |
| `ENV` | `dev` | Set to `production` to disable Swagger docs and `/debug/*` routes and switch logs to JSON |

> Note: `python-dotenv` is listed in requirements but never invoked — `.env`
> files are **not** loaded automatically; export variables in the shell.

## Development

```bash
uvicorn app.main:app --reload   # backend (port 8000 by default)
npm run dev                     # Vite dev build with Tailwind watching

ruff check .                    # lint
black .                         # format
```

Swagger UI is available at `/docs` and the OpenAPI schema at `/openapi.json`
while `ENV` is not `production`. A set of read-only debug endpoints lives under
`/debug/*` in dev only.

## Architecture overview

```
Browser (PWA, HTMX + Alpine.js)
   │  HTML over the wire
   ▼
FastAPI (app/main.py)
   ├── TenantMiddleware ── resolves tenant by Host header (PocketBase: tenants)
   │                    ── validates pb_auth cookie via PocketBase auth_refresh()
   ├── Routers (app/routes/**)        thin HTTP layer
   ├── Services (app/services/**)     PocketBase queries & business rules
   └── Jinja2 templates (RTL, Jalali dates)
   ▼
PocketBase (external)  ── collections: tenants, users, trainees, plans,
                          training_items, diet_items, steroid_items,
                          progress_logs, plan_progress, leads
                          + auth tokens + file storage (logos, progress photos)
```

Deeper material: [docs/04-architecture.md](docs/04-architecture.md),
[docs/05-api-reference.md](docs/05-api-reference.md).

## Project structure

```
app/
├── main.py            # FastAPI app assembly, version, docs gating
├── middleware.py      # TenantMiddleware (tenancy + auth + request logging)
├── templates.py       # Jinja2 env + Jalali date filters
├── pb.py              # PocketBase client factory (PB_URL)
├── utils.py           # hx_toast helper (HTMX toast headers)
├── logging_config.py  # structlog setup (console dev / JSON prod)
├── routes/            # feature routers (+ routes/user/ for trainee pages)
├── services/          # PocketBase access & business logic
├── templates/         # base, layouts, pages, forms, modals, components
└── static/            # built CSS/JS (Vite), service worker, fonts, swagger assets
data/                  # Persian exercise & food CSV datasets (dropdown sources)
exercises.json         # exercise dataset w/ Persian translations (data prep)
translate_exercises.py # offline script that builds exercises.json translations
Dockerfile             # python:3.11-slim, uvicorn on :8000
```

## Documentation

| Document | Audience |
| --- | --- |
| [Product overview](docs/01-overview.md) | Everyone — what Gyme is and what it does |
| [Getting started](docs/02-getting-started.md) | Developers setting up a dev environment |
| [User guide (فارسی)](docs/03-user-guide-fa.md) | Gym owners, coaches, trainees |
| [Architecture](docs/04-architecture.md) | Technical deep dive |
| [API reference](docs/05-api-reference.md) | All HTTP routes |
| [Configuration & deployment](docs/06-configuration-deployment.md) | Operators |
| [Troubleshooting & known issues](docs/07-troubleshooting-known-issues.md) | Everyone |

## Known limitations

Documented in detail in
[docs/07-troubleshooting-known-issues.md](docs/07-troubleshooting-known-issues.md).
Highlights:

- Deleting a plan item currently **always fails** (missing import in
  `app/routes/item.py` — see known issues for the one-line fix).
- Accounts created through the app start with **the email address as the
  password** until the user changes it.
- The `pb_auth` cookie is issued with `secure=False` even behind HTTPS.
- No automated tests, no CI configuration, and no LICENSE file in the repo.

## Deployment

A `Dockerfile` is provided (Python 3.11-slim, uvicorn on port 8000 with proxy
header support). Static assets must be built before the image is built because
Node/Vite files are excluded from the image. Full runbook:
[docs/06-configuration-deployment.md](docs/06-configuration-deployment.md).

## Contributing

There is no formal contribution process yet. Keep changes consistent with the
existing patterns (routes thin, logic in services, Persian UI strings, HTMX +
toast interaction style), and run `ruff check .` and `black .` before submitting.


## Internationalization (i18n)

Languages (cookie-based, Seoz pattern): **fa** (default, RTL), **en**, **es**, **tr**, **hy**.

- Switcher sets `locale` cookie for 1 year via `GET /locale/{code}?next=...` and full page reload.
- `<html lang dir>` follows the locale — RTL flips automatically for `fa`.
- UI strings: `_("…")` in Jinja and Python (Persian msgids + gettext catalogs under `app/locales/`).

```bash
make i18n-extract   # refresh messages.pot
make i18n-add LOCALE=de   # enable a new language (also flip enabled=True in app/i18n.py)
make i18n-update    # merge new msgids into existing .po files
make i18n-compile   # build .mo
```

To add a language: register it in `app/i18n.py` (`enabled=True`), `make i18n-add LOCALE=xx`, translate the `.po`, `make i18n-compile`.
