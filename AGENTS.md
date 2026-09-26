# Gyme: Agent Instructions

## Commands (Exact)

### Setup
```bash
# Python
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
.venv\Scripts\activate   # Windows
pip install -r app/requirements.txt

# Node (for Vite frontend build)
npm install
```

### Dev
```bash
# Start FastAPI (uvicorn)
uvicorn app.main:app --reload

# Start Vite dev server (parallel terminal, live CSS/JS)
npm run dev
```

### Build
```bash
# Build static assets (Vite → app/static/app.css + app.js, minified)
npm run build
```

### Test
```bash
make test     # = pytest -q
pytest        # run directly, fine too
```

### i18n (multilingual)
```bash
make i18n-extract        # refresh app/locales/messages.pot
make i18n-add LOCALE=de  # new catalog (also enable in app/i18n.py)
make i18n-update
make i18n-compile
pytest tests/test_i18n.py
```

### Lint/Format
```bash
# Ruff (lint)
ruff check .

# Black (format)
black .
```

## Architecture

### Stack
- **Backend**: FastAPI (Python 3.11+)
- **Frontend**: HTMX + Alpine.js + Tailwind CSS 4, built with Vite
- **Templates**: Jinja2 (locale-aware date filters; `_` / `ngettext` gettext)
- **DB**: PocketBase (via SDK)
- **i18n**: gettext catalogs under `app/locales/` (default locale **en**, which is also the source of msgids; `es`/`tr`/`hy` also enabled; all locales are LTR)

### Key Directories
```
app/
├── routes/       # FastAPI routers (feature-organized; user/ subfolder for trainee area)
├── services/     # Business logic: PocketBase queries, auth, filters, tenant scoping
├── static/       # Vite inputs (main.js, main.css) and built assets (app.css, app.js)
├── templates/    # Jinja2 templates (base, layouts, pages, forms, modals, components)
├── main.py       # FastAPI app setup
├── middleware.py # TenantMiddleware
├── security.py   # Auth cookies, sanitizers, allowlists, validators
├── i18n.py       # Locale registry + gettext plumbing
└── templates.py  # Jinja2 env (globals + locale-aware filters)
```

### Entry Points
- **FastAPI**: `app.main:app`
- **Templates**: `app/templates.py` (Jinja2 env + `_`/`ngettext`/`locale` globals + locale-aware filters)
- **Static**: `app/static/main.js` + `app/static/main.css` (Vite inputs)

### Quirks
- **Dates**: `loc_year` / `loc_date` filters in `templates.py` (also aliased `jalali_year` / `jalali_date`) render Gregorian dates via Babel (fallback `%Y-%m-%d`).
- **Swagger**: Disabled in production (`ENV=production` / `IS_PROD`).
- **Tenant Middleware**: Applied globally via `TenantMiddleware`; `GET /healthz` is served before any PocketBase call.
- **Auth cookie**: `pb_auth` via `app/security.set_auth_cookie` — `Secure` conditional on prod/https; login rate-limited 5 attempts/5 min per IP+identity+tenant.
- **Vite**: builds to `app/static/app.css` + `app/static/app.js` (committed; Python runs without Node).

## Constraints
- **Python**: 3.11+ (per `pyproject.toml`).
- **Node**: Required to rebuild static assets (Vite).
- **Env Vars**: `PB_URL`, `ENV` (`production` disables Swagger/docs), optional `ALLOWED_HOSTS` (TrustedHostMiddleware allowlist).
- **PocketBase**: Must be running (version ≥0.17.1) with a `tenants` record matching the request hostname.

## Workflow Order
1. **Setup**: Python venv + Node deps.
2. **Dev**: Run `uvicorn` + `npm run dev` in parallel.
3. **Build**: `npm run build` before deployment (regenerates `app/static/app.{css,js}`).
4. **Test**: `make test` (i18n + security regression suites).
5. **Lint**: `ruff check .` + `black .` (order irrelevant).

## Gotchas
- **Tailwind**: Vite + `@tailwindcss/vite`; edit `app/static/main.css`, rebuild with `npm run build`.
- **Jinja2 Filters**: Must be registered before template rendering.
- **New accounts**: initial password is random and never shown in the UI — staff must reset/share via PocketBase admin.
- **PocketBase**: No local mock → must be running for full functionality.

## References
- `pyproject.toml`: Ruff/Black config.
- `package.json`: Vite + Tailwind scripts (`dev`, `build`).
- `Makefile`: test + i18n targets.
- `app/requirements.txt`: Python deps.
- `app/templates.py`: Jinja2 env + locale-aware date filters.