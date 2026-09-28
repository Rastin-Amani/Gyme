# 06 — Configuration & Deployment

## Environment variables

| Variable | Default | Purpose |
| --- | --- | --- |
| `PB_URL` | `http://127.0.0.1:8090` outside production; required in production | External PocketBase base URL. Production warns if it uses plain HTTP. |
| `ENV` | `dev` | Set to `production` to disable Swagger/OpenAPI and debug routes and enable production logging/security behavior. |
| `ALLOWED_HOSTS` | unset | Optional comma-separated FastAPI `TrustedHostMiddleware` allowlist. Production logs a warning if unset. |
| `TRUSTED_PROXIES` | `127.0.0.1,::1` | Immediate peer IPs/CIDRs allowed to supply forwarded host/protocol/client-IP headers. Compose sets `172.28.0.2/32`. |
| `BACKEND_URL` | `http://backend:8000` in Compose | FastAPI origin used by the SvelteKit server. Use `http://127.0.0.1:8000` for local development. |

The application does not load `.env` files. Supply variables through the shell,
container environment, or process manager. Compose requires `PB_URL` and sets
`ENV=production`; configure `ALLOWED_HOSTS` as appropriate for the deployment.

## PocketBase setup

PocketBase is external to this repository and to `compose.yaml`. There is no
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

## Docker Compose deployment

The repository's `compose.yaml` builds two services:

- `frontend`: SvelteKit Node SSR server, exposed on the Compose network at port
  3000; route the public reverse proxy to this service.
- `backend`: FastAPI JSON API on port 8000, private to the Compose network.
- PocketBase is external; Compose does not create or publish a database.

Example:

```bash
PB_URL="https://pocketbase.example" \
ALLOWED_HOSTS="gym.example.com" \
docker compose -f compose.yaml up --build -d
```

The frontend is assigned `172.28.0.2`; the backend trusts forwarded headers
only from that exact peer (`TRUSTED_PROXIES=172.28.0.2/32`). Keep the backend
private and do not override this with broad proxy trust. Configure the public
proxy to forward the external host and protocol to SvelteKit; SvelteKit relays
that context to FastAPI, which validates the host and applies trusted-peer,
tenant, secure-cookie, and origin checks. Each served hostname must exactly match a
`tenants.domain` value.

`GET /healthz` on FastAPI is a process liveness check only; it does not test
PocketBase availability. Swagger UI (`/docs`), OpenAPI (`/openapi.json`), and
`/debug/*` are development-only. Do not use these endpoints as a production
readiness check.

## Production checklist

- [ ] Set `PB_URL` to the intended PocketBase instance over HTTPS.
- [ ] Set `ENV=production` and an appropriate `ALLOWED_HOSTS` allowlist.
- [ ] Review PocketBase API rules and backups at the PocketBase instance.
- [ ] Create tenant records for all public hostnames and owner accounts.
- [ ] Publish only the SvelteKit frontend; keep FastAPI private.
- [ ] Ensure the trusted frontend peer is the only source of forwarded headers.
- [ ] Confirm TLS termination and forwarded protocol handling at the public proxy.
- [ ] Remember login throttling is in-process (5 attempts per IP, identity, and
      tenant per 5 minutes); it is not shared between multiple replicas.

For local development setup, see [getting started](02-getting-started.md).
