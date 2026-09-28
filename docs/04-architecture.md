# 04 — Architecture

## System context

Gyme serves its browser UI from SvelteKit (Svelte 5, TypeScript,
`@sveltejs/adapter-node`). FastAPI provides the authenticated JSON API and owns
validation, tenant/role authorization, business rules, and persistence. An
external PocketBase instance stores records, auth data, and files.

```text
Browser
  └─ SvelteKit SSR + client navigation (public origin)
       ├─ HTML/pages, server loads and form actions
       └─ same-origin /api/v1/* proxy
            └─ private FastAPI /api/v1 JSON API
                 └─ services → external PocketBase
```

SvelteKit lives in `frontend/`. FastAPI's assembly, middleware, API router, and
business services live in `app/`. The backend does not render the application
UI; FastAPI's development Swagger page is API documentation only.

## Request and trust boundaries

1. The public request reaches the Node/SvelteKit frontend. SvelteKit SSR loads
   and form actions call the same-origin `/api/v1/*` proxy; browser code does
   not call PocketBase or the private backend directly.
2. The proxy forwards the browser cookie and request origin context, plus the
   public host/protocol and client address. FastAPI trusts forwarded values only
   when the immediate peer matches `TRUSTED_PROXIES`.
3. `compose.yaml` assigns the frontend `172.28.0.2`; the backend sets
   `TRUSTED_PROXIES=172.28.0.2/32` and exposes port 8000 only inside the Compose
   network. Do not publish that backend port or broaden proxy trust.
4. FastAPI resolves the tenant by exact public hostname against PocketBase's
   `tenants.domain`, validates the `pb_auth` token with PocketBase, then applies
   tenant and role checks in the API routes/services.
5. FastAPI returns JSON and semantic HTTP statuses. Failed upstream requests
   remain failures; the SvelteKit page layer does not treat them as successful
   mutations.

`pb_auth` is HttpOnly and SameSite=Lax; it is Secure in production. Login is
rate-limited in process by client IP, identity, and tenant (5 attempts per 5
minutes). Authenticated state-changing API requests require same-origin context;
only the trusted frontend peer may make the server-side BFF hop without an
Origin/Referer header. `GET /healthz` is a process liveness check and does not
contact PocketBase.

## API and data

The JSON API is rooted at `/api/v1` in `app/routes/api.py`; the SvelteKit proxy
exposes it on the public origin. API routes coordinate requests and authorization
while `app/services/` contains PocketBase queries and business logic. Main
collections used by the app are `tenants`, `users`, `trainees`, `plans`,
`training_items`, `diet_items`, `steroid_items`, `progress_logs`, and
`plan_progress`. The separate marketing application owns `leads`.

The repository does not define or migrate the PocketBase schema or API rules.
Field use can be traced in the services/API code, but operators must provision
the collections and review PocketBase rules for their deployment. FastAPI's
tenant/role checks do not replace restrictive PocketBase API rules, especially
because PocketBase file URLs may be fetched directly by browsers.

## Frontend and localization

`frontend/src/routes/` contains the SvelteKit page shell, server loads/actions,
same-origin API proxy, manifest/favicon handlers, and offline page. The public
page catch-all preserves the application's paths while data mutations and reads
go through FastAPI. Shared API helpers and UI translations are under
`frontend/src/lib/`; UI dictionaries for `en`, `es`, `tr`, and `hy` are in
`frontend/src/lib/i18n.ts`.

FastAPI/PWA messages use gettext catalogs in `app/locales/`. The two translation
systems are separate: backend Make targets update gettext catalogs, not the
Svelte dictionaries. Both the frontend locale cookie (`gyme_locale`) and
backend API locale support are allowlisted; all enabled locales are LTR.

## Build and deployment

- `npm --prefix frontend run check` type-checks the SvelteKit project;
  `npm --prefix frontend run build` creates the adapter-node server.
- `frontend/Dockerfile` builds and runs the Node SSR frontend on port 3000.
  The root `Dockerfile` builds FastAPI on port 8000.
- `compose.yaml` contains only `frontend` and `backend`; only the frontend is
  exposed for public routing. PocketBase is external.
- For local development, run FastAPI on port 8000 and SvelteKit on port 5173;
  set `BACKEND_URL=http://127.0.0.1:8000` and use a hostname present in the
  `tenants` collection.
- `ENV=production` disables FastAPI Swagger/OpenAPI and debug routes. The backend
  requires `PB_URL` in production; `.env` files are not loaded automatically.

## PWA endpoints and offline behavior

The public SvelteKit endpoints `/manifest.json` and `/favicon.ico` obtain
tenant-aware resources from FastAPI. The backend builds the manifest using the
resolved tenant and redirects the favicon to the tenant logo when configured.
SvelteKit owns the service worker and offline page. Its worker precaches the
current build/static assets, avoids `/api/` requests, and serves the bundled
offline page if a navigation fails; it does not provide a cached copy of
authenticated API data.

See [configuration & deployment](06-configuration-deployment.md) for the
operator settings and [API reference](05-api-reference.md) for JSON endpoints.
