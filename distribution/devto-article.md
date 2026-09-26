# Gyme on Dev.to — Full Article Draft

> Posting platform: Dev.to (also mirrorable to Hashnode with canonical URL).
> This is PREP, not publication — you review/hit publish. Add your own author
> line/disclosure where indicated. Re-verify facts (links, versions) before posting.

---

**Title:** Multi-tenant FastAPI: one codebase, N branded gym PWAs

**Tags:** `fastapi`, `python`, `webdev`, `showdev`

**Cover image:** none yet (repo has no screenshots — add a real UI capture when available; until then, post without cover or use a generated OG-style title card).

---

## Draft body

**TL;DR** — Gyme is an open-source (ISC) gym-coaching platform where every gym gets its own branded, installable PWA served from one FastAPI application. The tenancy trick is the `Host` header: `Host → PocketBase tenants → per-tenant manifest/theme/logo`. This post walks through the architecture and the tradeoffs we made.

### The problem

Gyms in our market were running coaching through WhatsApp and PDFs. Trainers hand out text-based plans, trainees lose them, progress is a chat log. Every coach we talked to wanted "an app" for their gym — with their logo, their colors, their name — but nobody wanted to pay for a custom build or lock themselves into Trainerize's pricing.

The naive solution is "one deployment per gym," which doesn't scale for a small team. We wanted **one codebase, many branded instances**, with gyms controllable as data, not as copies of the app.

### The approach: hostname-based tenancy

Tenancy is resolved from the HTTP `Host` header, not from a URL path:

```
Host: ironparadise.gyme.cloud
   └─→ PocketBase GET /collections/tenants?filter=domain='ironparadise.gyme.cloud'
           └─→ tenant: theme color, logo, manifest, PWA icons, locale defaults
```

A `TenantMiddleware` runs globally and resolves the tenant before routing. Because every request passes through it, no route can accidentally leak across tenants — the trust boundary is explicit at the edge.

Roles are scoped to the tenant context too: `owner` (the gym), `coach` (their own trainees and plans), `trainee` (reads "today" from their plan, marks steps done). PocketBase handles auth; the app validates the `pb_auth` cookie (`auth_refresh`) and re-checks tenant scoping on every protected call.

### The stack

| Layer | Pick | Why |
| --- | --- | --- |
| API/web | FastAPI | thin routers; all PocketBase queries live in `app/services/`, not in routes |
| Front end | HTMX + Alpine.js | HTML over the wire; no SPA build complexity for server-driven UI |
| Styling | Tailwind + daisyUI within Vite | one design system, built once, cached everywhere |
| Data | PocketBase (external) | realtime-capable, SQLite-backed per instance; no ORM/migrations to maintain |
| PWA | per-tenant manifest + service worker | each gym gets an installable, offline-capable home-screen app |
| i18n | gettext (Babel) | `en` (default), `es`, `tr`, `hy` — all LTR with Gregorian dates |

The pleasant surprise: because UI is server-rendered HTML with HTMX for interactivity, a "branded app per gym" is mostly a template concern — theme variables, manifest JSON, and locale plumbing — not N front-end builds.

### Tradeoffs we made (be honest about these)

- **PocketBase as the data layer:** no migration framework, and the app depends on an external service being up. We keep `GET /healthz` served before any PocketBase call so load balancers can probe without DB coupling.
- **`Host` is the tenant boundary:** it works great for dedicated domains per gym, but it's a strong coupling to DNS/reverse-proxy configuration — documented prominently.
- **Production hygiene:** Swagger/docs are disabled when `ENV=production`; `ALLOWED_HOSTS` enable Host-header hardening; auth cookies are `Secure` on HTTPS.
- **One known rough edge:** an admin creates users with a random 15-character password that is never displayed — staff must reset passwords through PocketBase admin. It's a deliberate vault-ish default, but not a great UX yet.

### What ships

- **Self-host:** one Dockerfile (`python:3.11-slim`, uvicorn on `:8000`, non-root). Node is not in the image — static assets are pre-built with Vite and committed.
- **i18n that matters locally:** four locales (en/es/tr/hy) behind gettext, all left-to-right with Gregorian dates — not an afterthought.
- **Progress tracking:** trainee body metrics auto-compute BMI, body-fat percentage, BMR, TDEE, LBM, and waist-to-hip ratio, with up to 5 photos per log.

### Numbers

~55 tests (i18n + security-regression + known-issue suites), green CI (ruff, black, pytest). 225 commits, 6 releases, v0.9.1 current. First release 2026-06-14.

### Try it

- Source: https://github.com/Rastin-Amani/Gyme
- Docs (getting started, architecture, API, deployment, troubleshooting): in-repo `docs/`
- Docker: `ghcr.io/Rastin-Amani/Gyme` (image; set to public) — run with `PB_URL` pointing at your PocketBase
- Managed hosting: https://gyme.cloud *(verify this link is live before posting)*

**Disclosure:** I built Gyme. Happy to go deep on the tenancy model or the multi-locale date handling — ask away.

---

## Pre-post checklist

[ ] Verify gyme.cloud is reachable (or drop the link)
[ ] Add one real screenshot when available (cover + in-body)
[ ] Confirm version text (0.9.1) and repo URL
[ ] Publish with your Dev.to handle; set canonical URL
[ ] Don't reuse this body on HN/Reddit — those have their own drafts