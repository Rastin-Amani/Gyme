# Gyme on Dev.to — Full Article Draft

> Posting platform: Dev.to (also mirrorable to Hashnode with canonical URL).
> This is PREP, not publication — you review/hit publish. Add your own author
> line/disclosure where indicated. Re-verify facts (links, versions) before posting.
> **Architecture update (2026-09-28):** this draft was revised from its earlier
> HTMX/Jinja description to match the SvelteKit frontend and FastAPI JSON API.

---

**Title:** Multi-tenant gym coaching with SvelteKit, FastAPI, and PocketBase

**Tags:** `fastapi`, `python`, `webdev`, `showdev`

**Cover image:** none yet (repo has no screenshots — add a real UI capture when available; until then, post without cover or use a generated OG-style title card).

---

## Draft body

**TL;DR** — Gyme is an open-source (ISC) gym-coaching platform where every gym gets its own branded, installable PWA from one Compose deployment. SvelteKit serves the UI and proxies same-origin requests to a private FastAPI JSON API. Tenant resolution uses the public hostname: `Host → PocketBase tenants → per-tenant manifest/theme/logo`.

### The problem

Gyms in our market were running coaching through WhatsApp and PDFs. Trainers hand out text-based plans, trainees lose them, progress is a chat log. Every coach we talked to wanted "an app" for their gym — with their logo, their colors, their name — but nobody wanted to pay for a custom build or lock themselves into Trainerize's pricing.

The naive solution is "one deployment per gym," which doesn't scale for a small team. We wanted **one deployment, many branded instances**, with gyms controllable as data, not as copies of the app.

### The approach: hostname-based tenancy

Tenancy is resolved from the HTTP `Host` header, not from a URL path:

```
Host: ironparadise.gyme.cloud
   └─→ PocketBase GET /collections/tenants?filter=domain='ironparadise.gyme.cloud'
           └─→ tenant: theme color, logo, manifest, PWA icons, locale defaults
```

A `TenantMiddleware` resolves the tenant on FastAPI requests before protected API routes run. The public host reaches the backend through the trusted SvelteKit proxy; tenant resolution and authorization remain server-side.

Roles are scoped to the tenant context too: `owner` (the gym), `coach` (their own trainees and plans), `trainee` (reads "today" from their plan, marks steps done). PocketBase handles auth; the app validates the `pb_auth` cookie (`auth_refresh`) and re-checks tenant scoping on every protected call.

### The stack

| Layer | Pick | Why |
| --- | --- | --- |
| Frontend | SvelteKit + Svelte 5 + TypeScript | SSR pages and form actions call the same-origin API proxy |
| API/web | FastAPI | JSON API and authorization; PocketBase queries live in `app/services/` |
| Styling | Tailwind CSS with Caldera styles | shared UI tokens in the Svelte frontend |
| Data | PocketBase (external) | realtime-capable, SQLite-backed per instance; no ORM/migrations to maintain |
| PWA | tenant-aware manifest + SvelteKit service worker | per-gym installable app and offline navigation fallback |
| i18n | Svelte dictionaries + backend gettext | `en` (default), `es`, `tr`, `hy` — all LTR |

The pleasant surprise: each gym's hostname and PocketBase tenant record select its branding and manifest. The same SvelteKit build serves all tenants; no per-gym frontend build is needed.

### Tradeoffs we made (be honest about these)

- **PocketBase as the data layer:** no migration framework, and the app depends on an external service being up. `GET /healthz` is a process liveness check and does not contact PocketBase.
- **`Host` is the tenant boundary:** it works great for dedicated domains per gym, but it's a strong coupling to DNS/reverse-proxy configuration — documented prominently.
- **Production hygiene:** Swagger/docs and debug routes are disabled when `ENV=production`; `ALLOWED_HOSTS` enables FastAPI host validation; forwarded headers are trusted only from the configured frontend peer; auth cookies are Secure in production.
- **One known rough edge:** app-created users get a random 15-character password that is never displayed — staff must set/reset it through PocketBase admin before first login.

### What ships

- **Self-host:** `compose.yaml` runs a Node/SvelteKit frontend on port 3000 and a private Python/FastAPI API on port 8000; PocketBase remains external.
- **i18n that matters locally:** four UI locales (en/es/tr/hy), all left-to-right. Svelte UI dictionaries and backend gettext catalogs are maintained separately.
- **Progress tracking:** trainee body metrics auto-compute BMI, body-fat percentage, BMR, TDEE, LBM, and waist-to-hip ratio, with up to 5 photos per log.

### Numbers

Before publication, verify current version, test/CI status, release history, and first-release date against the live repository; this draft's old figures are intentionally removed.

### Try it

- Source: https://github.com/Rastin-Amani/Gyme
- Docs (getting started, architecture, API, deployment, troubleshooting): in-repo `docs/`
- Docker: `compose.yaml` builds the two app services — set `PB_URL` to your external PocketBase
- Managed hosting: https://gyme.cloud *(verify this link is live before posting)*

**Disclosure:** I built Gyme. Happy to go deep on the tenancy model or the SvelteKit/FastAPI split — ask away.

---

## Pre-post checklist

[ ] Verify gyme.cloud is reachable (or drop the link)
[ ] Add one real screenshot when available (cover + in-body)
[ ] Confirm current version and repo URL
[ ] Publish with your Dev.to handle; set canonical URL
[ ] Don't reuse this body on HN/Reddit — those have their own drafts
