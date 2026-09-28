# 07 — Troubleshooting & Known Issues

These checks describe the current SvelteKit frontend and FastAPI JSON API.

## Frontend does not start or pages appear unstyled

- Install dependencies with `npm --prefix frontend ci` and start development
  with `npm --prefix frontend run dev` (port 5173).
- Check frontend build/type errors with `npm --prefix frontend run check` and
  `npm --prefix frontend run build`.
- In Compose, route the browser to the Node frontend service on port 3000. The
  root FastAPI `Dockerfile` is the private API service, not the browser UI.

## API requests fail or show service unavailable

- Confirm FastAPI is running at the configured `BACKEND_URL` (`127.0.0.1:8000`
  for local development; `backend:8000` inside Compose).
- Confirm `PB_URL` reaches the external PocketBase service. It defaults to
  `http://127.0.0.1:8090` outside production and is required when
  `ENV=production`.
- Check FastAPI logs and the PocketBase service. `/healthz` tests FastAPI only;
  it does not contact PocketBase.

## Login or tenant lookup fails

- The current browser hostname must exactly match a `domain` value in
  PocketBase's `tenants` collection. For local development, use a local hosts
  entry and visit the SvelteKit server using that tenant hostname.
- In Compose, ensure the reverse proxy forwards the public host and protocol to
  SvelteKit. The frontend-to-backend request supplies those values to FastAPI;
  forwarded headers are trusted only from the configured immediate proxy peer.
- Confirm the user belongs to the resolved tenant and the PocketBase auth
  collection/API rules allow the requested operations.
- Login is limited to 5 attempts per IP, identity, and tenant per 5 minutes.
  The limiter is in memory, so it resets on process restart and is not shared
  across replicas.
- App-created accounts have a random initial password that is not displayed;
  staff need to set/reset it through PocketBase administration before the user
  can sign in.

## FastAPI `/docs` or `/debug/*` returns 404

This is expected when `ENV=production`. In development, Swagger is available at
`http://127.0.0.1:8000/docs`; debug routes are also development-only.

## CSRF or permission errors

The SvelteKit server-side proxy forwards the browser's origin context and auth
cookie. Do not call the private backend directly from browser code or expose
port 8000 publicly. FastAPI checks authentication, tenant ownership, role, and
same-origin context; a hidden or disabled UI control is not authorization.

## Progress photo rejected

The API accepts at most 5 progress photos per request, each up to 5 MB. It checks
the filename, extension, declared image type, and file signature; accepted types
are JPEG, PNG, WebP, and GIF.

## Deployment notes and known limits

- PocketBase schema and API rules are configured outside this repository. The
  code cannot verify that deployed collection rules are sufficiently restrictive.
- Login rate limiting is process-local; deployments with multiple replicas need
  an upstream/shared limiter if consistent cross-replica throttling is required.
- Password changes do not use the login rate limiter.
- Service worker caching covers frontend build/static resources and an offline
  navigation fallback. It does not cache `/api/` responses or authenticated app
  data for offline use.
