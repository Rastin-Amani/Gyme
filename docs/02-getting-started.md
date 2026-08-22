# 02 — Getting Started (Development)

**Verification status:** every command below was checked against the repository
(`package.json`, `vite.config.js`, `Dockerfile`, `app/requirements.txt`,
`pyproject.toml`). Note that `AGENTS.md` in the repo root still references
`npm run css:watch` / `css:build` scripts — those **do not exist** anymore; the
frontend is now built with Vite. See known issues.

---

## Prerequisites

| Tool | Requirement | Evidence |
| --- | --- | --- |
| Python | 3.11+ | `pyproject.toml` targets `py311`; Docker image is `python:3.11-slim` |
| Node.js + npm | Modern version supported by Vite 8 | `package.json` devDependencies (`vite ^8`) |
| PocketBase | A reachable instance you control | all data access goes through it; the Python SDK requirement is `pocketbase>=0.17.1`. The *server* version itself is not pinned anywhere in this repo — use a current release |

## 1. Python setup

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r app/requirements.txt
```

Installed stack: FastAPI, uvicorn, pocketbase (SDK), Jinja2, python-multipart,
python-dotenv, pydantic-settings, requests, jdatetime, jalali_core, pandas,
openpyxl, structlog.

## 2. Frontend assets

The UI uses Tailwind CSS 4 + daisyUI, compiled by Vite from
`app/static/main.js` / `app/static/main.css`:

```bash
npm install
npm run build     # one-off build → app/static/app.js + app/static/app.css (+ assets/)
# or
npm run dev       # Vite watch mode while developing
```

Vite config details (from `vite.config.js`):

- Base path `/static/`, output directory `app/static`, `emptyOutDir: false`.
- JS entry is emitted as `app.js`; CSS as `app.css`; fonts go to `assets/[name]-[hash][extname]`.

Prebuilt `app/static/app.css` and `app/static/app.js` are committed, so the
server runs even without a frontend build — but rebuild whenever templates'
Tailwind classes change, otherwise new classes won't have styles.

## 3. Configure environment variables

Two environment variables exist (there is no committed `.env.example`):

| Variable | Default | Meaning |
| --- | --- | --- |
| `PB_URL` | `http://db.dev.gyme.cloud` | PocketBase base URL used by every request (`app/pb.py`). ⚠️ The default points at the project's remote **dev** database — always set your own for local work |
| `ENV` | `dev` | `production` hides Swagger docs + `/debug/*` routes and switches logging to JSON |

> **`.env` files are not loaded.** `python-dotenv` is installed but never called.
> Export variables in your shell or process manager:
>
> ```bash
> export PB_URL="http://127.0.0.1:8090"
> # export ENV=production   # only for prod-like runs
> ```

## 4. Prepare PocketBase

The app expects these collections to exist (fields are inferred from code — see
[06-configuration-deployment.md](06-configuration-deployment.md) for field-level
detail): `tenants`, `users`, `trainees`, `plans`, `training_items`,
`diet_items`, `steroid_items`, `progress_logs`, `plan_progress`, `leads`.

Minimum to boot a usable gym:

1. Create the collections above with the fields listed in the configuration doc.
2. Create a `tenants` record whose `domain` matches the hostname you will use,
   e.g. `yourgym.local`, and set its `name` and (optionally) `logo`/theme fields.
3. Make sure `users` is an auth collection with `role`, `tenant`, `first_name`,
   `last_name`, `phone` fields and that API rules permit what the app needs
   (the app talks to PocketBase as an admin-less client using user tokens after
   login; creation of users/trainees happens with whatever rule set your
   instance defines — **Unverified:** the repo cannot confirm your instance's
   API rules).

## 5. Run

```bash
uvicorn app.main:app --reload          # serves http://127.0.0.1:8000
```

Then open the app **through a hostname matching a tenant domain**, e.g. add to
`/etc/hosts`:

```
127.0.0.1   yourgym.local
```

and browse `http://yourgym.local:8000`. This matters because tenancy is derived
from the `Host` header:

- Unknown host → tenant is unresolved → login attempts show
  «خطای سیستم: باشگاه یافت نشد!».
- Host of the record marked main (`is_main=true`) → public landing page at `/`.
- Any other known host → `/` redirects to `/dashboard` (logged-in) or `/login`.

## 6. Developer conveniences

- Swagger UI at `/docs`, OpenAPI JSON at `/openapi.json` (non-production only).
- Debug endpoints under `/debug/*` (non-production only) dump raw tenant/user/
  plan records as JSON — useful for inspecting expand behavior.
- Logs: structlog pretty console output in dev; add `req_id` and `tenant_id` to
  each line via middleware context.

## Lint & format

```bash
ruff check .    # line-length 100, py311 target
black .         # line-length 100
```

Templates are additionally formatted with Prettier (plugins for Jinja and
Tailwind class sorting are in `package.json` / `.prettierrc`).

## Troubleshooting setup

See [07-troubleshooting-known-issues.md](07-troubleshooting-known-issues.md)
for symptom-based diagnostics (blank styles, login failures, unknown-domain
errors, etc.).
