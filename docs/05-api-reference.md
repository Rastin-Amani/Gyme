# 05 — HTTP Route Reference

**Verification status:** compiled directly from the routers registered in
`app/main.py` (`app/routes/**`). Every path, parameter name, and response
behavior below is traceable to code. This documents the app's own endpoints;
PocketBase endpoints are external and out of scope.

---

## Conventions

**Authentication & tenancy**

- Everything except the public paths (`/login`, `/logout`, `/static/*`,
  `/manifest.json`, `/sw.js`, `/favicon.ico`, `/locale`) requires a valid
  `pb_auth` cookie; anonymous requests get `303 → /login` from middleware.
  `/` always `303`s to `/dashboard` (authenticated) or `/login` (anonymous),
  and `/healthz` is served before auth checks (PB-free liveness, returns
  `{"status": "ok"}`).
- Requests are scoped to the tenant resolved from the Host header.
- Role guards inside handlers: any `owner`/`coach`-side route redirects
  trainees (`303 → /user/dashboard`), and `/user/*` routes redirect
  non-trainees (`303 → /dashboard`).

**Content types**

- Reads return full HTML pages or HTML fragments (`text/html`).
- Writes (HTMX form posts) usually return an **empty body with headers**:
  - `200` + `HX-Trigger-After-Swap: {"show-toast":{"message":"…","type":"…"}}`
    (toast payload built by `app/utils.hx_toast`)
  - `204` + `HX-Trigger: {…}` for modal-driven flows, often combining
    `show-toast`, `closeModal`, `refreshList`, and/or `delayed-redirect:{url}`
  - `303` redirects for classic navigations (login, role redirects)
- All request bodies use form encoding (`application/x-www-form-urlencoded` or
  `multipart/form-data`; `python-multipart` is installed). There is no JSON
  API surface.

**Pagination** — list endpoints take `page` (1-based, `ge=1`) and render 5
items per page (20 for coaches). Responses carry `page`, `total_pages`,
`total` into the template context.

---

## Authentication

| Method | Path | Purpose | Notes |
| --- | --- | --- | --- |
| GET | `/login` | Login page with tenant branding | Already-authenticated users are sent to `/dashboard` (which then forwards trainees onward) |
| POST | `/login` | Password login against PocketBase `users` | Fields: `identity`* (email), `password`*. Wrong credentials ⇒ toast "Wrong email or password."; an account belonging to a *different* gym ⇒ the raw service error string `Invalid tenant access` is shown as the toast (logged as `login_cross_tenant_denied`). Success: `303` to `/user/dashboard` (role `trainee`) else `/dashboard`; sets `pb_auth` cookie (`HttpOnly`, `SameSite=Lax`, `Secure` conditional on prod/https). **Rate limited** in-memory to 5 attempts per 5 minutes per IP+identity+tenant; on limit a `429` toast "Too many login attempts. Please wait a few minutes." is shown and further attempts for that key are blocked until the window expires (the key is cleared on successful login) |
| GET | `/logout` | Logout (no-op page) | Clears the `pb_auth` cookie + auth store, `303 → /login` |
| POST | `/logout` | Logout | Same clearing as GET; `303` + `HX-Redirect: /login` |
| GET | `/change-password` | Change-password page | Requires login (`303 /login` otherwise) |
| POST | `/change-password` | Rotate password | Fields: `old_password`*, `new_password`*, `confirm_password`*. Server checks match, length 8–72 chars, and that the new password is not a substring of the account email (toasts "New password and its confirmation do not match." / "Password must be at least 8 characters." / "Password is too long" / "Password must not be similar to the email"). On PocketBase success (toast "Password changed successfully! 🔒") it re-authenticates with the new password, resets the cookie, and answers `HX-Redirect` to the role's dashboard; if re-auth fails the stale cookie is cleared and the redirect goes to `/login` |
| GET | `/locale/{code}?next=…` | Switch language | `code` must be in the enabled locales (`en`,`es`,`tr`,`hy`) else `404`; sets the `locale` cookie (1 year) and `303`s to `next` (open-redirect guarded) |
| GET | `/healthz` | Liveness | Served by middleware before tenant lookup; returns `{"status": "ok"}` with **no PocketBase call** |

## Owner / coach area

### Dashboard

| Method | Path | Purpose | Notes |
| --- | --- | --- | --- |
| GET | `/dashboard?timeframe=all\|week\|month` | Owner dashboard page (stats + coach performance) | Trainees redirected. When `hx-target: dashboard-content` header is present, returns only the `components/dashboard_content.html` fragment (timeframe dropdown) |
| GET | `/dashboard/coach-stats` | Coach-stats fragment (`components/coach_stats.html`) | Used for partial refreshes; owners see all coaches + themselves, coaches see only their row |
| GET | `/dashboard/debug-coach-stats` | JSON dump of raw plan/progress counts | ⚠️ Registered unconditionally (not part of the ENV-gated `/debug` router) — available in production too, though still behind authentication |

### Trainees

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/trainees?page&query&gender&status&min_birthdate&max_birthdate` | List page (5/page) |
| GET | `/trainees/search?query&page&gender&status&min_birthdate&max_birthdate` | Same rendering flagged as search result |
| GET | `/trainees/filter?gender&status&min_birthdate&max_birthdate&page` | Filter-only variant |
| GET | `/trainees/new` | Create form ("New trainee") |
| POST | `/trainees/new` | Create account + profile (see below) |
| GET | `/trainees/{id}` | Detail page incl. plans, progress logs, photo file URLs |
| GET | `/trainees/{id}/edit` | Edit form |
| POST | `/trainees/{id}` | Update user record + profile record |
| GET | `/trainees/{id}/confirm-delete` | Delete confirmation modal |
| DELETE | `/trainees/{id}` | Delete profile record |

Create/update form fields (identical for both):
`first_name`*, `last_name`*, `email`*, `phone`, `gender`, `birthdate`,
`blood_type`, `training_history`, `steroid_history`, `supplement_history`,
`limitations`, `notes`.

Behavior details:

- **Create** runs two writes: `services/auth.create_user` (random initial
  password — never the email — and `role="trainee"`), then `trainees.create`
  (status defaults `active`). Success responds with toast "Trainee registered
  successfully. Redirecting..." plus `delayed-redirect` to
  `/progress-log/new/{trainee_id}`. The random password is **not displayed in
  the UI**; staff must share/reset it via PocketBase admin. User-creation
  failure surfaces the duplicate/short-email toast (a legacy message);
  profile write failures hit the generic server-error toast.
- **Update** writes the contact fields to the linked `users` record and the
  rest to the `trainees` record, then `delayed-redirect` to the detail page.
- **Delete** removes only the `trainees` record (the auth user remains),
  toasting "Trainee deleted successfully." and redirecting to `/trainees`.
- Coach scoping: when the caller has role `coach`, listing/search/filtering is
  restricted to trainee ids found on that coach's plans.

### Coaches (effectively owner-only; no explicit owner guard)

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/coaches?page` | List page (20/page), users with `role="coach"` in tenant |
| GET | `/coaches/new` | Create form |
| POST | `/coaches/new` | Fields: `first_name`*, `last_name`*, `email`*, `phone`. Creates `users` record with `role="coach"` and a **random initial password** (never the email; not displayed in the UI — reset via PocketBase admin) |
| GET | `/coaches/{id}` | Detail page |
| GET | `/coaches/{id}/edit` | Edit form |
| POST | `/coaches/{id}` | Update the user record (verifies tenant+role first) |
| GET | `/coaches/{id}/confirm-delete` | Delete confirmation modal |
| DELETE | `/coaches/{id}` | Deletes the `users` record entirely (revokes login) |

### Plans & templates

| Method | Path | Purpose | Notes |
| --- | --- | --- | --- |
| GET | `/plans?page&query&type&coach_id&is_template` | Plan list (5/page); `is_template=true` renders "Plan templates" | Coaches forced to their own plans. Search matches `template_name` or expanded trainee names. The coach filter dropdown reads `users` with `role="coach"` (issue #4 resolved in 0.9.1) |
| GET | `/plans/new?template=false` | Create form; `template=true` shows "Template name" instead of trainee selector | Coach `<select>` lists current user first + tenant coaches from `users` |
| POST | `/plans` | Create plan or template | Fields: `type`* (`training`\|`diet`\|`steroid`), `trainee`, `start_date`, `end_date`, `days_per_week`, `status`, `notes`, `is_template` (`true/on/1/yes`), `template_name`, `coach`. Templates null-out `trainee`/`template_name` handling accordingly; default status `active` |
| GET | `/plans/{id}` | Plan detail with its items | Items read from `{type}_items` collection sorted by `seq`,`order` |
| GET | `/plans/{id}/edit` | Edit form | |
| POST | `/plans/{id}` | Update plan/template (same fields as create) | |
| GET | `/plans/{id}/confirm-delete` | Delete confirmation modal | |
| DELETE | `/plans/{id}` | Delete plan (items remain orphaned in PocketBase) | |
| GET | `/templates/{id}/apply` | Apply-template modal (coach, trainee, dates, notes) | Template must have `is_template=true` |
| POST | `/templates/{id}/apply` | Instantiate template | Fields: `trainee`*, `start_date`, `end_date`, `notes`, `coach` (defaults to caller). Copies plan header + every item into `{type}_items` under the new plan id. Success `204` + `closeModal` + toast + delayed redirect to the new plan. Error toasts distinguish 404 ("Template or trainee not found!") vs 400 ("Invalid input. Please check the dates.") vs generic DB error |

> Note: the owner profile page links "Change password" to `/change-password`
> (known issue #6, resolved in 0.9.1).

### Plan items

Item endpoints exist per plan type; `plan_type` selects the PocketBase
collection (`training_items`, `diet_items`, `steroid_items`) and which subset
of fields is persisted:

| plan_type | Persisted item fields |
| --- | --- |
| `training` | `name` ← form `item_name`, `seq`, `order`, `sets`, `reps`, `weight`, `rest_seconds`, `category` (Warm-up / Corrective / Main / Cardio / Cool-down), `notes` |
| `diet` | `name` ← form `food_name`, `meal_name`, `quantity`, `seq`, `order`, `notes` |
| `steroid` | `name` ← form `name`, `type`, `dosage`, `frequency`, `seq`, `order`, `notes` |

| Method | Path | Purpose | Notes |
| --- | --- | --- | --- |
| GET | `/items/new?plan_type={t}&plan_id={p}` | Add-item modal (with exercise/food datalists) | |
| POST | `/items` | Create item | Fields: `plan_type`*, `plan`* + type-specific fields above |
| GET | `/items/{id}/edit?plan_type={t}` | Edit-item modal | |
| POST | `/items/{id}` | Update item | `plan` only forwarded when it doesn't look like a collection-prefix value |
| GET | `/items/{id}/confirm-delete?plan_type={t}` | Delete confirmation modal | |
| DELETE | `/items/{id}?plan_type={t}` | Delete item | ✅ Works in 0.9.1 (delete bug fixed in 0.9.0 via a lazy in-handler import — see known issue #1). Responds `204` + `closeModal` + `refreshList`. |

Success responses here are `204` with `closeModal` (+ `refreshList` on
update/delete) and an English success toast.

### Progress logs (assessments)

| Method | Path | Purpose | Notes |
| --- | --- | --- | --- |
| GET | `/progress-log/new/{trainee_id}` | Initial assessment form ("Record initial assessment") | Unknown trainee → redirect `/trainees` |
| POST | `/trainees/{trainee_id}/progress-log` | Create log | See field handling below |
| GET | `/progress-log/{log_id}/edit` | Edit modal (`modals/progress_log_edit.html`) | |
| POST | `/progress-log/{log_id}` | Update log | Responds with `HX-Trigger-After-Swap` carrying `closeModal` + `performListRefresh` |

Fields accepted as **strings** and parsed defensively (`safe_float`, blank →
`None`; invalid height/weight fall back to `0.0`): `height`*, `weight`*,
`chest`, `waist`, `hip`, `arms`, `notes`, plus client-computed `bmi`, `bfp`,
`bmr`, `tdee`, `lbm`, `whr`.

Photo upload rules enforced server-side: max **5 files**, each ≤ **5 MB**,
content types limited to `image/jpeg`, `image/png`, `image/webp`, `image/gif`
(violations raise `HTTPException 400` with an English message). Files attach to
the `progress_photos` field of the `progress_logs` record.

Both create and update also sync `height`/`weight` onto the linked `trainees`
record, then toast success and (create only) delayed-redirect to the trainee
detail page.

### Profile

| Method | Path | Purpose | Notes |
| --- | --- | --- | --- |
| GET | `/profile` | Owner/coach profile page | Shows account info; owners additionally see tenant domain/theme and the coaches-management card |

## Trainee area (`/user/*`)

| Method | Path | Purpose | Notes |
| --- | --- | --- | --- |
| GET | `/user/dashboard` | "Today" view: per-plan current-day items across diet/training/steroid tabs | Non-trainees redirected to `/dashboard` |
| POST | `/user/plans/{plan_id}/done` | Advance the plan's day pointer | Recomputes distinct `seq` values of the plan's items, advances `current_seq` with wrap-around in `plan_progress` (creating it on first use), replies `200` + `HX-Refresh: true` |
| GET | `/user/plans` | Trainee's plan list page | |
| GET | `/user/plans/{id}` | Full plan detail (all days/items) | No ownership check beyond tenant scoping (**Unverified** whether cross-trainee access within a gym matters operationally) |
| GET | `/user/profile` | Trainee profile page | |

## PWA endpoints

| Method | Path | Purpose | Notes |
| --- | --- | --- | --- |
| GET | `/manifest.json` | Per-tenant web app manifest | Icons from tenant logo via PocketBase thumbs (`192x192f`, `512x512f`) or bundled fallbacks; standalone portrait, theme/background `#1d232a`, `start_url=/login` |
| GET | `/sw.js` | Service worker source | `__CACHE_VERSION__` substituted with `APP_VERSION` at request time; served with `Service-Worker-Allowed: /`, `Cache-Control: no-cache` |
| GET | `/offline/` | Offline fallback page (inline HTML) | Cached by the service worker |
| GET | `/favicon.ico` | Redirects to 32×32 thumb of tenant logo, else static favicon | |

## Static assets

`GET /static/*` serves `app/static/` (mounted in `main.py`): Vite-built
`app.css`/`app.js`, hashed fonts under `assets/`, self-hosted workbox modules
(`js/workbox-*.prod.js`), Swagger UI assets (`swagger/*`), icons, fonts.

## Development-only endpoints

Registered by `main.py` only while `ENV != "production"`:

| Method | Path | Returns |
| --- | --- | --- |
| GET | `/docs` | Custom Swagger UI page (self-hosted assets) |
| GET | `/openapi.json` | OpenAPI schema |
| GET | `/debug/tenant` | Current tenant id/domain/name |
| GET | `/debug/planexpand` | First raw plan record of the tenant |
| GET | `/debug/planitems` | Items of a **hardcoded** plan id (`guhobjjzu2jt2kv`) |
| GET | `/debug/traineeitems` | Raw trainee list |
| GET | `/debug/useritems` | Current user object |
| GET | `/debug/usertest` | Current user + trainee + categorized plan dicts |
| GET | `/debug/test` | Current user id + tenant id |
| GET | `/debug/userplans` | Current user's trainee plans |

(Additionally, `GET /dashboard/debug-coach-stats` exists in **all**
environments — see the dashboard table above.)

## Quick smoke test from the CLI

```bash
# Login (stores the session cookie)
curl -i -c cookies.txt -X POST https://YOUR-GYM-DOMAIN/login \
  --data-urlencode "identity=EMAIL@example.com" \
  --data-urlencode "password=YOUR_PASSWORD"

# Authenticated page fetch (HTML)
curl -b cookies.txt https://YOUR-GYM-DOMAIN/dashboard -o dashboard.html
```

Replace placeholders (`YOUR-GYM-DOMAIN`, credentials) — none of these values
exist in the repository.
