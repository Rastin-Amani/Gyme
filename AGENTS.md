# Gyme: Agent Instructions

## Stack

- Backend: FastAPI, Python 3.11+, PocketBase SDK.
- Frontend: SvelteKit, Svelte 5, TypeScript, `@sveltejs/adapter-node`.
- Styling: Tailwind CSS 4 and the existing Caldera visual tokens in
  `frontend/src/routes/app.css`.
- Production: one Compose app with private FastAPI `backend` and public Node SSR
  `frontend` services. PocketBase is external.
- Internationalization: Svelte UI dictionaries in `frontend/src/lib/i18n.ts`;
  FastAPI/PWA messages use gettext catalogs in `app/locales/`. Enabled locales
  are en, es, tr, and hy, all LTR.

## Commands

### Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r app/requirements.txt
npm --prefix frontend ci
```

### Development

Run FastAPI and SvelteKit in separate terminals. Set `PB_URL` to the local or
remote PocketBase instance and `BACKEND_URL` for the SvelteKit BFF. Use a
hostname present in the `tenants` collection, e.g. `gym.localhost`.

```bash
uvicorn app.main:app --reload --port 8000
npm --prefix frontend run dev
```

Open the SvelteKit dev server on port 5173. FastAPI's dev Swagger is available
directly at `http://127.0.0.1:8000/docs`.

### Build and checks

```bash
npm --prefix frontend run check
npm --prefix frontend run build
.venv/bin/python -m pytest -q  # or: make test
ruff check .
black --check .
```

The Node adapter output is `frontend/build/`; it is generated and should not be
committed. For a production-like deployment, use `docker compose -f compose.yaml
up --build` with `PB_URL` configured.

### Backend gettext catalogs

```bash
make i18n-extract
make i18n-add LOCALE=de
make i18n-update
make i18n-compile
```

These Make targets update backend gettext messages only. Svelte UI translations
must also be added to `frontend/src/lib/i18n.ts`.

## Architecture

```text
Browser
  └── SvelteKit SSR + client navigation (public same-origin app)
        └── private /api/v1 BFF proxy
              └── FastAPI API -> services -> PocketBase (external)
```

- SvelteKit page `load` functions and form actions call the same-origin BFF.
- FastAPI owns authentication, role/tenant authorization, validation, data
  mutation, and PocketBase access. Never move business rules to the browser.
- `pb_auth` remains HttpOnly; never expose PocketBase tokens or credentials to
  client-side JavaScript.
- FastAPI middleware trusts forwarded host/protocol/client-IP data only from
  the exact frontend proxy peer configured in Compose. Do not broaden proxy
  trust or publish backend port 8000.
- `/healthz` does not access PocketBase. `/docs`, OpenAPI and JSON debug routes
  are development-only. Keep tenant resolution and open-redirect checks intact.
- The SvelteKit catch-all route currently dispatches the existing public URL
  space; preserve its routes, query parameters, form behavior, and HTTP status
  semantics when changing it.
- Dynamic `/manifest.json` and `/favicon.ico` are proxied from FastAPI so
  tenant branding remains origin-local. SvelteKit owns its service worker and
  offline page.

## Project layout

```text
app/
├── routes/api.py       # JSON API
├── routes/pwa.py       # Tenant-aware manifest/favicon
├── routes/debug.py     # Development diagnostics
├── services/           # PocketBase access and business rules
├── middleware.py       # Tenant, auth, proxy trust, CSRF, security headers
├── security.py         # Cookies, sanitizers, host and redirect validation
├── i18n.py             # Backend locale registry/gettext
└── static/swagger/     # Development API docs assets
frontend/
├── src/routes/         # SvelteKit pages, actions, BFF and PWA endpoints
├── src/lib/            # UI, API client, locale dictionaries
├── src/service-worker.ts
└── package.json        # SvelteKit + adapter-node dependencies
tests/                  # Python/API/security/i18n tests
compose.yaml            # Exactly the frontend and backend services
```

## Security and behavior constraints

- Preserve role checks (`owner`, `coach`, `trainee`) and tenant-scoped record
  access in FastAPI. Hiding a control in Svelte is not authorization.
- Preserve login rate limiting, secure/HttpOnly/SameSite cookies, CSRF Origin /
  Referer validation, forwarded-host validation, and safe redirects.
- Never trust client-provided tenant, role, or record IDs. Validate uploads and
  do not expose PocketBase admin credentials.
- Keep semantic HTTP statuses for JSON APIs and SSR page errors. Do not turn
  failed upstream requests into a successful page response.
- Use accessible semantic controls, labels, keyboard operation, visible focus,
  responsive layouts, and reduced-motion support.
- No HTMX, Alpine.js, Jinja UI, or alternate frontend framework. Do not inject
  legacy HTML into Svelte.

## References

- `pyproject.toml`: Ruff/Black configuration.
- `app/requirements.txt`: Python runtime dependencies.
- `frontend/package.json`: frontend scripts and dependencies.
- `Makefile`: Python tests and backend i18n targets.
- `docs/04-architecture.md`: request/security and data-flow details.
- `docs/06-configuration-deployment.md`: Dokploy/Compose runbook.
