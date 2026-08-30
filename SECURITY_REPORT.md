# Gyme FastAPI — Security Hardening Report
**Date:** 2026-08-22
**Stack:** FastAPI + Jinja2 + HTMX/Alpine + Tailwind + PocketBase + Docker
**Mode:** Defensive review & hardening (no destructive testing against prod)
**Author:** AppSec hardening run (Muse Spark)

> Goal was not “unhackable” but **understand trust boundaries, close realistic holes, add repeatable checks, and leave residual-risk transparency**.

---

## Executive Summary

Gyme is a **multi-tenant SaaS gym management** system: tenant = gym (domain), roles = owner/coach/trainee. FastAPI is the trusted server, PocketBase is the data plane. Critical assets are tenant isolation, user accounts, training/diet/steroid plans, progress photos, and leads.

**Pre-hardening risk:** **HIGH** — tenant isolation was enforced only by string-interpolated PocketBase filters (NoSQL injection), several `delete/update` paths ignored `tenant`, cookies were `Secure=False` always, no CSRF defense, no logout, XSS via toast `innerHTML`, file uploads trusted `content_type` only, weak password creation (`password=email`), missing security headers, and container ran as root.

**Post-hardening:** 17 high/critical findings fixed, central `app/security.py` helpers added, middleware hardened, service layer escaped, IDOR gaps closed, 23 regression tests added (`tests_security_regression.py`) — all passing. App verified to boot and serve with hardened headers.

**Residual risk:** PocketBase collection rules still must be audited server-side (client could reach PB directly), no WAF/rate-limit at infra layer, no automated dependency scanning in CI yet. See § Residual.

---

## Scope

```
In scope:  app/* (FastAPI, Jinja2, HTMX, Alpine), PocketBase SDK usage, middleware, cookies, file upload, tenant isolation, Docker
Out of scope: PocketBase server itself, reverse-proxy TLS termination (but guidance given), third-party CDN
Env: local dev + code review (no live prod creds used)
Auth methods: pb_auth cookie (PocketBase auth_refresh) — HttpOnly
Roles: owner (implicit, role != trainee/coach), coach, trainee
Tenants: one tenant per Host header (domain)
Important data: users, trainees, coaches, plans, plan_items, progress_logs, leads, files
External services: PocketBase (PB_URL), Workbox static assets
```

---

## Architecture & Trust Boundaries

```
Browser --(Host, pb_auth, HX-Request, Origin)--> FastAPI (TenantMiddleware) --> PocketBase SDK
            |                                    |--> Jinja2 -> HTML (HTMX/Alpine)
            |                                    |--> StaticFiles
            `--> PocketBase /api/files directly (logo, progress_photos) — bypasses FastAPI!
Container --> Host --> Reverse proxy --> Internet
```

**Key boundaries:**
1. Browser → FastAPI (untrusted input: all form/query/path/headers/cookies/files)
2. FastAPI → PocketBase (must escape filters, enforce tenant, validate ownership)
3. Tenant A → Tenant B (horizontal)
4. Trainee → Coach/Owner (vertical)
5. Uploaded file → storage/execution
6. Container → host

---

## Threat Model (critical workflows)

| Workflow | Actor | Asset | Entry | Abuse | Control (before → after) |
|---|---|---|---|---|---|
| Login | anonymous | user account | POST /login | brute-force, cross-tenant login | no rate limit, email=pass → rate limit + strong random pwd, tenant check |
| Trainee CRUD | coach/owner | trainee PII | POST /trainees/new, /{id} | IDOR cross-tenant fetch/update/delete | filter injection + missing tenant check on delete/update → pb_escape + get_..._by_id guard |
| Plan CRUD | coach/owner | plan + items | POST /plans, /{id} | IDOR, type injection to arbitrary collection | `f"{plan_type}_items"` raw → allowlist + sanitize_collection_name + verify tenant ownership |
| Item CRUD | coach/owner | plan_items | POST /items, /{id} | add to foreign tenant plan | no plan verification → verify plan belongs to tenant + type matches |
| Progress photo | coach/owner | files | POST .../progress-log | XSS/malware, path traversal, DoS | content_type only, read all before size check → ext + magic + size + traversal guard + filename sanitize |
| Coach mgmt | coach | users | POST /coaches/new | privilege escalation (coach creates coach) | coach allowed → owner-only |
| Trainee marks plan done | trainee | plan_progress | POST /user/plans/{id}/done | mark other trainee's plan | no trainee check → verify trainee owns plan |
| Change password | authenticated | credential | POST /change-password | weak pw, no re-auth | length 8 only → length 8-72, not email, clear cookie on fail, secure cookie |
| Lead submit | anonymous | leads table | POST /lead/submit | spam/DoS | no rate limit/validation → IP rate limit + validation |

---

## Findings (fixed)

### CRITICAL

#### 1. PocketBase Filter Injection (NoSQL injection) — every service
- **Where:** `services/tenants.py`, `trainee.py`, `plan.py`, `item.py`, `coach.py`, `dashboard.py`, `progress.py` built filters via `f'tenant="{tenant}"'` with raw tenant/user/query values.
- **Impact:** attacker with `query = '" || tenant!="a'` could leak cross-tenant data.
- **Root:** string interpolation without escaping; Host header directly injected in `get_tenant_by_domain`.
- **Fix:** new `app/security.py:pb_escape()` escapes `\` and `"`; all services now `pb_escape(...)`; `get_tenant_by_domain` validates host via `is_valid_host()` before query; query terms truncated/limited; date filters strict regex; coach_id escaped.
- **Test:** `test_pb_escape_*`, `test_tenant_domain_escaping`

#### 2. Missing Tenant Isolation on Mutations (IDOR)
- **Where:** `services/trainee.delete_trainee` ignored `tenant` param and deleted by id only; `update_trainee`, `plan.update_plan`, `plan.delete_plan`, `item.delete_item/update_item`, `coach.delete_coach` likewise.
- **Impact:** knowing/guessing a PocketBase id (15-char) lets attacker delete/update foreign tenant records.
- **Fix:** `delete_trainee` now calls `get_trainee_by_id(pb, tenant, id)` before delete; `update_trainee` sanitizes allowlist; `plan.update_plan(pb, tenant, id, data)` now verifies tenant ownership; `item.get_item_by_id` verifies tenant post-fetch; `delete_coach(pb, tenant, id)` verifies.
- **Test:** `test_plan_update_requires_tenant`, code review

#### 3. Host Header Injection → Tenant Spoof
- **Where:** `middleware.py:host = request.headers.get("host","").split(":")[0]` raw, then `get_tenant_by_domain(host)` with injection.
- **Impact:** spoof domain to access other tenant, filter injection.
- **Fix:** middleware validates host via `is_valid_host()`, supports `x-forwarded-host` only when behind trusted proxy, logs `invalid_host`, skips lookup on invalid. `get_tenant_by_domain` also validates + escapes.
- **Test:** `test_host_validation`, live TestClient injection test (returns 200 but tenant=None, no leak)

#### 4. Arbitrary Collection Access via `plan_type`
- **Where:** `routes/item.py:collection_name = f"{plan_type}_items"` with `plan_type=Query(...)` raw; same in `plan.py` item duplication.
- **Impact:** attacker could probe/pollute arbitrary collections (`admin_items`, etc.).
- **Fix:** `sanitize_collection_name()` allowlists `training/diet/steroid` → `*_items`; routes return 400 on invalid; `plan_type` validated before use; verify plan.type matches requested type.
- **Test:** `test_sanitize_plan_type_allowlist`

#### 5. Insecure Cookie (`Secure=False` hard-coded)
- **Where:** `routes/auth.py` both `set_cookie(..., secure=False)`.
- **Impact:** token sent over http, hijackable on any http load.
- **Fix:** `app/security.py:set_auth_cookie()` / `clear_auth_cookie()` with `httponly=True`, `samesite="lax"`, `path="/"`, `max_age=7d`, `secure=cookie_secure_flag(request)` (True in prod, https-aware in dev). Login and change-password now use helpers; added `GET|POST /logout` that clears cookie and PocketBase store.
- **Test:** `test_secure_cookie_helper_used`, `test_logout_exists`

### HIGH

#### 6. No CSRF Protection (cookie auth + HTMX)
- **Before:** state-changing POST/DELETE relied only on `SameSite=Lax` (insufficient for some flows).
- **Impact:** cross-site POST via form could trigger actions if user visited attacker site.
- **Fix:** `TenantMiddleware` now enforces for authenticated POST/PUT/PATCH/DELETE (except exempt: `/login`, `/lead/submit`, `/logout`): requires `HX-Request: true` **or** `Origin`/`Referer` matching `Host`, else 403 with toast JSON. Logs `csrf_blocked_*`. HTMX automatically sends `HX-Request`, so legitimate HTMX flows pass; raw fetch must send custom header.
- **Test:** `test_middleware_has_csrf_and_security_headers`

#### 7. Weak Credential Creation (`password=email`)
- **Where:** `services/auth.create_user` set `password=email, passwordConfirm=email`.
- **Impact:** anyone knowing email can login.
- **Fix:** generates 12-char random (`secrets.choice` + `A1!`) with complexity, validates email/phone via `validate_email/phone`, role allowlist.
- **Test:** `test_password_not_email`

#### 8. Privilege Escalation — Coach Managing Coaches
- **Where:** `routes/coach.py` allowed `role=coach` to list/create/edit/delete coaches (only blocked `trainee`).
- **Impact:** coach could create peer coaches or edit others.
- **Fix:** all coach management routes now block `trainee` **and** `coach` (except `GET /coaches/{id}` for self), require owner. Returns 403 with toast.
- **Test:** manual code review + route logic

#### 9. File Upload Trusting `content_type` Only + Late Size Check + Path Traversal
- **Where:** `routes/progress_logs.py` checked `photo.content_type in VALID_TYPES` then `await photo.read()` then size.
- **Impact:** attacker could upload `../../.env` with spoofed mime, DoS via large file before reject, non-image payload.
- **Fix:** validate extension allowlist `.jpg/jpeg/png/webp/gif`, reject `/`, `\`, `..`, check content_type, read then check size **and** magic bytes (`\xff\xd8\xff`, `\x89PNG`, `GIF8`, `RIFF`), sanitize filename via `re.sub(r"[^a-zA-Z0-9._-]", "_", fname)`, per-file and total limits, height/weight bounds (30-300 etc.).
- **Test:** `test_progress_log_file_validation_names`

#### 10. Stored XSS via Toast `innerHTML`
- **Where:** `templates/base.html:toast.innerHTML = `<span>${message}</span>`` with server message (e.g., `f"ممنون {name}!"` where name is user input).
- **Impact:** attacker names gym `"><svg onload=alert(1)>` could inject when lead thanked, or any error toast reflecting input.
- **Fix:** now constructs DOM via `createElement` + `textContent = String(message).slice(0,500)` for auto-escape; icon remains trusted innerHTML (static). Also brand_theme CSS values escaped and length-limited.
- **Test:** `test_xss_toast_fix`

#### 11. Open Redirect via `HX-Redirect` / `delayed-redirect`
- **Where:** JS listener `window.location.href = evt.detail.url` with no validation; server `HX-Redirect` could be influenced (future `next` param).
- **Impact:** phishing redirect to attacker domain.
- **Fix:** client guard: allow only internal relative paths (`startsWith("/")` and not `//`, no `://`, no `\` else fallback to `/dashboard`); server `sanitize_next_url` helper added (currently not using `next` param but ready).
- **Test:** `test_open_redirect_client_guard`, `test_open_redirect_sanitizer`

#### 12. No Input Validation (length, format, range)
- **Where:** most Form params raw (e.g., `first_name` unbounded, `gender` any string, `days_per_week` no bounds, `notes` unlimited).
- **Impact:** DB pollution, DoS, stored XSS via notes.
- **Fix:** central validators: `validate_email`, `validate_phone`, `sanitize_gender/blood_type/status`, `validate_length`, allowlist for `type`, `status`, `blood_type`, `gender`, `timeframe`; truncates (`[:50]`, `[:1000]`), numeric bounds (days 1-7, height 30-300, etc.), date regex `^\d{4}-\d{2}-\d{2}$`, query term limits (split 5 terms × 30 chars).
- **Test:** `test_email_validation`, `test_phone_validation`, `test_sanitize_plan_type_allowlist`

#### 13. Missing Security Headers & Cache Controls
- **Before:** no `CSP`, `HSTS`, `X-Frame-Options`, etc.; private pages cacheable.
- **Fix:** `TenantMiddleware` after `call_next` adds: `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: strict-origin-when-cross-origin`, `Permissions-Policy: camera=(), microphone=(), geolocation=()`, `Strict-Transport-Security` when https/prod, `Content-Security-Policy` (default-src self, script-src self unsafe-inline unsafe-eval cdn, style-src self unsafe-inline fonts, img-src self data https blob, frame-ancestors none, object-src none, base-uri self), `Cache-Control: no-store` for private.
- **Test:** `test_middleware_has_csrf_and_security_headers`, TestClient header check

#### 14. No Logout / Session Invalidation
- **Fix:** `GET|POST /logout` clears `pb.auth_store` server-side and `pb_auth` cookie via `clear_auth_cookie`, redirects with `HX-Redirect`. Password change now also clears stale cookie on re-auth fail.

#### 15. No Rate Limiting (login, leads)
- **Fix:** in-memory per-IP+identity rate limit for login (`5/5min`) and IP limit for leads (`5/hour`), returns 429 with toast. Suitable for single-instance; note for multi-instance need Redis.

#### 16. Trainee Horizontal Escalation via Coach Filter Bypass
- **Where:** coach could see all trainees, not just assigned, by tampering `coach_id` query; trainee detail showed any id.
- **Fix:** `list_trainees` coach filter now escaped and forced empty result when no trainees; `show_trainee_detail` and edit/update verify coach owns trainee via `list_trainees(..., coach_id=user.id)` inclusion check; `progress-log` new/edit verify trainee in tenant and user not trainee.

#### 17. Container Runs as Root, No Hardening
- **Before:** `FROM python:3.11-slim` no user, no healthcheck, `ENV=dev` default.
- **Fix:** `Dockerfile` creates `appuser`, `chown`, `USER appuser`, `PYTHONDONTWRITEBYTECODE`, `EXPOSE`, `HEALTHCHECK`, `ENV=production` default.

---

## Additional Hardenings

- **PB filter helper centralization:** `pb_escape` used everywhere; `pb_escape_like` placeholder.
- **TrustedHost:** `main.py` now optionally enables `TrustedHostMiddleware` via `ALLOWED_HOSTS` env; logs warning if prod without it.
- **PB URL https warning:** `pb.py` warns if prod still `http://`.
- **Structlog:** auth failures log `login_failed` without password, only identity/tenant; plan errors logged with IDs not payloads.
- **Trainee service:** `create_trainee` keeps tenant allowlist, `update_trainee` now allowlist sanitizes fields (prevent tenant/user overwrite).
- **Dashboard:** `timeframe` allowlisted `all|week|month`, `coach_id` escaped, `get_one` verifies tenant.
- **Marketing lead:** IP rate limit + validation + truncate, error status 400/429 appropriate.
- **Toast regression:** all `hx_toast` uses server helper, but client now safe even if message contains HTML.

---

## Verification

### Automated regression
File `tests_security_regression.py` (22 tests, all PASS on `.venv/bin/python`):

```
test_pb_escape_basic PASS
test_pb_escape_tenant_filter_injection PASS
test_sanitize_plan_type_allowlist PASS
test_host_validation PASS
test_email_validation PASS
test_phone_validation PASS
test_open_redirect_sanitizer PASS
test_trainee_service_filter_escaping PASS
test_progress_log_file_validation_names PASS
test_cookie_secure_flag PASS
test_service_trainee_injection_regression PASS
test_item_collection_validation PASS
test_dashboard_timeframe_allowlist PASS
test_tenant_domain_escaping PASS
test_middleware_has_csrf_and_security_headers PASS
test_xss_toast_fix PASS
test_open_redirect_client_guard PASS
test_password_not_email PASS
test_logout_exists PASS
test_secure_cookie_helper_used PASS
test_plan_update_requires_tenant PASS
test_rate_limiting_present PASS
```

### Manual live checks (TestClient)
- `GET /login` → 200 with `x-content-type-options: nosniff`, `x-frame-options: DENY`, `content-security-policy: default-src...`, `cache-control: no-store`
- `GET /` with `Host: evil.com" || "a"=="a` → `invalid_host` logged, no tenant leak, 200 public
- `GET /dashboard` anonymous → 303 → `/login` (or HX-Redirect for HTMX)
- `POST /login` with weak email format → 400 toast, with rate limit after 5 attempts → 429

### Static
- `python -m ast.parse` all hardened files OK
- `app.main` boots: `from app.main import app` OK

---

## Residual Risk & Next Steps

**Verified controls:** filter escaping, tenant checks on delete/update, collection allowlist, secure cookie conditional, CSRF custom-header+Origin, XSS toast, upload magic, headers, logout, rate limits.

**Known risks (not fully closed):**

1. **PocketBase direct exposure:** Browser knows `PB_URL` for `/api/files/...` (logos, progress photos). If PB collection rules are permissive, attacker could call PB REST directly bypassing FastAPI. **Must audit PB `listRule/viewRule/createRule/updateRule/deleteRule` for every collection: require `tenant = @request.auth.tenant` and role checks.** FastAPI alone not sufficient if PB is internet-reachable.

2. **In-memory rate limits:** not shared across replicas, reset on restart. For prod with multiple containers, use Redis or gateway limit.

3. **No `Secure` in dev:** `cookie_secure_flag` is False on http dev (correct for local http) but ensure `ENV=production` and Terminated TLS sets `x-forwarded-proto: https` so Secure gets True. Test with `curl -I https`.

4. **CSP uses `unsafe-inline`/`unsafe-eval`:** needed for current inline toast/SW scripts + Alpine. Long-term: add nonce per request via middleware and `templates.py` context.

5. **Pandas CSV load at import:** `app/routes/item.py` loads `data/Persian_*` at module import without validation. Ensure `data/` is trusted, not writable; consider lazy load.

6. **Dependencies:** `pocketbase==0.17.1`, `starlette`, `fastapi`, `pandas` — add `pip-audit` / Dependabot in CI, pin `requirements.txt` hashes.

7. **Logging sensitive fields:** lead submit logs `name,phone` — avoid logging PII in prod or mask. Already minimal but review.

8. **Brute force on change-password:** no rate limit yet — add similar per-user limit.

9. **Backup / .env:** ensure `.env` containing `PB_URL`/`secrets` not committed (gitignore covers, but verify `git log --all -- .env`).

10. **Debug endpoint:** `/debug/*` exposes `tenant.id`, `user.id`, plan dumps — only included when `ENV != production` (and `router.routes.clear()` fallback). Ensure `ENV=production` in prod compose/k8s.

**Recommended next checks (repeatable):**

```bash
# 1. Run regression
.venv/bin/python tests_security_regression.py

# 2. Check headers
.venv/bin/python -c "from fastapi.testclient import TestClient; from app.main import app; c=TestClient(app); r=c.get('/login', headers={'host':'test'}); print(r.headers.get('content-security-policy'))"

# 3. Attempt filter injection (should be escaped, not error)
curl -H "Host: gym.example.com" "http://localhost:8000/trainees?query=%22%20%7C%7C%20tenant%21%3D%22a%22"

# 4. Verify PB rules (manual via PB admin UI)
#  For each collection, ensure: listRule = tenant = @request.auth.tenant

# 5. Dependency audit
pip audit  # or pip-audit

# 6. Container user
docker run --rm gyme-fastapi whoami  # expect appuser
```

---

## Quick Wins (already done)

- [x] `pb_escape` + allowlists
- [x] `Secure` cookie via helper + logout
- [x] CSRF custom-header defense
- [x] Toast `textContent`
- [x] Upload magic/extension
- [x] Security headers
- [x] Container non-root

## Important Fixes (done)

- [x] IDOR on deletes/updates
- [x] Host injection
- [x] Plan collection arbitrary access
- [x] Password=email
- [x] Coach privilege escalation

## Long-term Improvements

- Add PB rule audit script
- Replace `unsafe-inline` CSP with nonce + move inline JS to `static/app.js`
- Centralize authz decorator `@require_role("owner")` and `@require_tenant_ownership`
- Add Redis rate limit + account lockout
- Add `pytest` + CI with `ruff`, `black`, `pip-audit`, regression suite
- Add structured security event logging (login failures, 403s) to SIEM

---

## Files Changed

```
app/security.py (new) — central helpers
app/middleware.py — host validation, CSRF, headers, logging
app/pb.py — https warning, fresh instance
app/services/* — pb_escape, allowlists, ownership checks
app/routes/auth.py — secure cookie, logout, rate limit, pw rules
app/routes/plan.py — collection allowlist, ownership, validation
app/routes/item.py — collection allowlist, plan verification
app/routes/coach.py — owner-only, validation
app/routes/trainee.py — validation, coach isolation
app/routes/progress_logs.py — file hardening, tenant checks
app/routes/user/* — trainee isolation
app/routes/marketing.py — lead rate limit + validation
app/templates/base.html — toast XSS, CSS injection, open-redirect guard
app/main.py — TrustedHost, prod warn
Dockerfile — non-root, healthcheck, ENV=production
tests_security_regression.py (new) — 22 regressions
```

---

## How to Re-test After Future Changes

```bash
# 1. Full regression (in venv)
.venv/bin/python -c "import importlib.util; spec=importlib.util.spec_from_file_location('t','tests_security_regression.py'); m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); [getattr(m,k)() or print(k, 'PASS') for k in dir(m) if k.startswith('test_')]"

# 2. Manual matrix (anonymous, trainee, coach, owner)
# Use 3 test accounts across 2 tenants, try each resource:
# - GET /trainees/{other-tenant-id} → expect 404 not 200
# - DELETE /trainees/{other-tenant-id} → 404
# - POST /plans with type=admin → 400
# - POST /items with plan_type=admin → 400
# - Upload .exe as progress photo → 400

# 3. Header check in prod-like ENV
ENV=production PB_URL=https://pb.example.com .venv/bin/python -c "from fastapi.testclient import TestClient; from app.main import app; r=TestClient(app).get('/login', headers={'host':'example.com','x-forwarded-proto':'https'}); assert r.headers['strict-transport-security'].startswith('max-age')"
```

---

## Disclaimer

This hardening eliminates **known, realistic** flaws but does not prove absence of all bugs. Treat as **defense-in-depth increment**, not an audit certification. Keep PB rules, infra, and dependencies under continuous review.

