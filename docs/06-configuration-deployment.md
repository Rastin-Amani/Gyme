# 06 — Configuration & Deployment

## Environment variables

| Variable | Default | Purpose |
| --- | --- | --- |
| `PB_URL` | `http://127.0.0.1:8090` outside production; required in production | External PocketBase base URL. Production warns if it uses plain HTTP. |
| `ENV` | `dev` | Set to `production` to disable Swagger/OpenAPI and debug routes and enable production logging/security behavior. |
| `ALLOWED_HOSTS` | unset | Optional comma-separated FastAPI `TrustedHostMiddleware` allowlist. Production logs a warning if unset. |
| `TRUSTED_PROXIES` | `127.0.0.1,::1` | Immediate peer IPs/CIDRs allowed to supply forwarded host/protocol/client-IP headers. The production container needs no override: the SvelteKit BFF is the loopback peer. |
| `BACKEND_URL` | `http://127.0.0.1:8000` | FastAPI origin used by the SvelteKit server. The production image sets this internal loopback address; local development uses the same value. |

The application does not load `.env` files. Supply variables through the shell,
container environment, or process manager. The production image requires
`PB_URL` and sets `ENV=production`; configure `ALLOWED_HOSTS` with the public
hostnames (the entrypoint appends the internal `127.0.0.1` peer
automatically).

## PocketBase setup

PocketBase is external to this repository. There is no
schema migration or seed script here. Provision a tenant record for every
public hostname and the collections/fields used by the app:

| Collection | Fields used by the application |
| --- | --- |
| `tenants` | `domain`, `name`, `logo`, `theme`, `brand_theme`, `brand_colors`, `primary_color` |
| `users` (auth) | `email`, `password`, `first_name`, `last_name`, `phone`, `tenant`, `role` |
| `trainees` | `user`, `tenant`, `status`, `gender`, `birthdate`, `blood_type`, `height`, `weight`, `training_history`, `steroid_history`, `supplement_history`, `limitations`, `notes` |
| `plans` | `tenant`, `type`, `trainee`, `coach`, `start_date`, `end_date`, `days_per_week`, `status`, `notes`, `is_template`, `template_name` |
| `training_items` | `tenant`, `plan`, `name`, `category`, `seq`, `order`, `sets`, `reps`, `weight`, `rest_seconds`, `notes` |
| `diet_items` | `tenant`, `plan`, `name`, `meal_name`, `quantity`, `seq`, `order`, `notes` |
| `steroid_items` | `tenant`, `plan`, `name`, `type`, `dosage`, `frequency`, `seq`, `order`, `notes` |
| `progress_logs` | `tenant`, `trainee`, metric fields, `notes`, `progress_photos` |
| `plan_progress` | `tenant`, `plan`, `current_seq` |

These are fields referenced by code, not a complete PocketBase schema
specification. Exact field types, indexes, and API rules are deployment choices
the repository cannot verify. Review PocketBase list/view/create/update/delete
rules for each role and tenant. FastAPI checks do not protect requests made
directly to an internet-reachable PocketBase server; file URLs may also be read
directly by browsers.

Create at least one owner account in PocketBase admin before first use. The app
has no public signup flow. Accounts created through the app receive a random
initial password that is not shown in the UI; staff must arrange an initial
password reset/share through PocketBase administration.

## Single-container Docker deployment (Dokploy)

The root `Dockerfile` builds one image containing both services:

- `frontend`: SvelteKit Node SSR server, the only public listener (port 3000).
- `backend`: FastAPI JSON API bound to `127.0.0.1:8000` inside the container;
  it is unreachable from outside the container.
- `docker-entrypoint.sh` supervises both processes: if either exits, the other
  is stopped and the container exits, so the orchestrator restarts a complete
  app instead of leaving a half-running container. The image healthcheck probes
  a frontend static asset and FastAPI's PB-independent `/healthz`.
- PocketBase is external; the image creates no database.

Example (plain Docker):

```bash
PB_URL="https://pocketbase.example" \
ALLOWED_HOSTS="gym.example.com" \
docker build -t gyme . && docker run -d -p 3000:3000 gyme
```

Dokploy settings for this repository (Application → type **Dockerfile**):

| Setting | Value |
| --- | --- |
| Git repository / branch | this repository, `main` |
| Build Path (Dockerfile location) | `Dockerfile` (repository root) |
| Build Context Directory | `/` (repository root) |
| Port | `3000` (the only exposed port; never add 8000) |
| Environment | `PB_URL=https://pocketbase.example`, `ALLOWED_HOSTS=gym.example.com` |

No Compose file or service networking exists: SvelteKit reaches FastAPI via
`BACKEND_URL=http://127.0.0.1:8000`, which the image sets by default. The
backend trusts forwarded headers only from the loopback BFF peer, and the
entrypoint appends `127.0.0.1` to `ALLOWED_HOSTS` so the trusted-host check
accepts that internal hop. Configure the public proxy (Dokploy's Traefik) to
forward the external host and protocol to port 3000; SvelteKit relays that
context to FastAPI, which validates the host and applies trusted-peer,
tenant, secure-cookie, and origin checks. Each served hostname must exactly
match a `tenants.domain` value.

`GET /healthz` on FastAPI is a process liveness check only; it does not test
PocketBase availability. Swagger UI (`/docs`), OpenAPI (`/openapi.json`), and
`/debug/*` are development-only. Do not use these endpoints as a production
readiness check.

## Production checklist

- [ ] Set `PB_URL` to the intended PocketBase instance over HTTPS.
- [ ] Set `ENV=production` and an appropriate `ALLOWED_HOSTS` allowlist.
- [ ] Review PocketBase API rules and backups at the PocketBase instance.
- [ ] Create tenant records for all public hostnames and owner accounts.
- [ ] Publish only port 3000; FastAPI binds loopback inside the container and
      must never be added as an exposed port.
- [ ] Ensure the only source of forwarded headers is the in-container SvelteKit
      BFF (the `TRUSTED_PROXIES` loopback default).
- [ ] Confirm TLS termination and forwarded protocol handling at the public proxy.
- [ ] Remember login throttling is in-process (5 attempts per IP, identity, and
      tenant per 5 minutes); it is not shared between multiple replicas.

For local development setup, see [getting started](02-getting-started.md).
