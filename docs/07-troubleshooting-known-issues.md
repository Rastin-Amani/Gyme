# 07 — Troubleshooting & Known Issues

**Verification status:** every issue below was confirmed by reading the source
at the current working tree (version 0.9.1, verified 2026-09-25). File/line
references are included so each claim can be checked. Issues are numbered;
other documents reference these numbers. Statuses: **OPEN** (still true),
**RESOLVED** (fixed in the current tree), **PARTIAL**.

---

## Part 1 — Troubleshooting by symptom

### Styles are broken / page renders unstyled

1. Check whether built assets exist: `ls app/static/app.css app/static/app.js`.
2. If you changed templates/Tailwind classes recently, rebuild: `npm run build`
   (Vite writes to `app/static`, `emptyOutDir=false`).
3. Hard-refresh once; afterwards the service worker's stale-while-revalidate
   strategy self-heals CSS/JS on the next load (see `app/static/sw.js`).

### Login shows "System error: Gym not found!"

The hostname you're browsing is not any gym's domain.

1. Compare your browser URL's hostname with `tenants.domain` records.
2. Add a matching `tenants` record or browse via a mapped hostname (dev tip:
   `/etc/hosts` entry, e.g. `127.0.0.1 yourgym.local`). Evidence:
   `middleware.py` resolves tenants by Host header; `routes/auth.py` returns
   this exact toast when `request.state.tenant` is missing.

### Login fails ("Wrong email or password.") although credentials seem right

1. Confirm the account belongs to *this* gym: logins from another tenant's
   account are deliberately rejected (`login_cross_tenant_denied`,
   `services/auth.py`).
2. Check PocketBase reachability: look for `auth_refresh_failed` /
   `login_failed` warnings in app logs.
3. Remember new accounts get a **random** initial password that the UI never
   displays — if the user never changed it, neither you nor they can know it;
   reset it in PocketBase admin (issue #3).
4. Note the login rate limit: 5 wrong attempts within 5 minutes for the same
   IP+identity+gym trips the in-memory limiter, which then blocks further
   attempts (toast "Too many login attempts. Please wait a few minutes.", `429`). Wait out
   the window or restart the app to clear it (dev only).

### Everything errors right after a deployment

1. Verify `PB_URL` is set for the container/process — the default silently
   points at the project's dev server (`app/pb.py`, issue #8).
2. Verify PocketBase is reachable from the app host (`curl $PB_URL/api/health`
   against your instance).
3. If JSON logs show `request.error` with tenant-related tracebacks on every
   authenticated route, the serving hostname has no `tenants` record (issue
   #15).

### Creating a trainee fails

Toast "Could not create the user. (The email may already be in use or the
password is too short)" means the underlying `users.create` failed: duplicate
email, invalid email format, or (legacy message reuse) email shorter than 8
characters — the message predates 0.9.0, when the initial password equaled the
email; passwords are now generated randomly. Evidence: `routes/trainee.py`,
`services/auth.create_user`.

### Deleting a plan item always shows an error

**Fixed in 0.9.0.** The lazy import added inside the DELETE handler
(`routes/item.py` line ~114) resolved the `NameError`; deletes now reach
PocketBase and respond `204` + `closeModal` + `refreshList`. If you still see
an error toast, hard-refresh to drop a stale service worker (see issue #1 for
history).

### Trainee sees every exercise grouped under "Other"

Known bug, issue #2: the movement category chosen in the item modal is not
persisted, so the trainee dashboard's grouping finds nothing. Items still
display, just without their category heading.

### Old styles persist after deploying a new version

PWA caches are keyed by `APP_VERSION` (`sw.js` `__CACHE_VERSION__` replaced by
`routes/pwa.py`). If clients keep old assets, confirm you bumped `APP_VERSION`
in `app/main.py` (and ideally `app/version.text`) before building. Note the
hardcoded `sw.js?v=…` query in `base.html` is currently out of sync (issue #7)
— it affects SW script freshness checks, not asset caches.

### Progress photos rejected

Limits enforced server-side (`routes/progress_logs.py`): max **5 files**, each
≤ **5 MB**, types JPEG/PNG/WebP/GIF only. The form previews and validates the
same rules client-side before upload.

### Swagger `/docs` or `/debug/*` returns 404

Expected when `ENV=production`. Set `ENV` to something else (or unset) in
non-production environments. Exception: `GET /dashboard/debug-coach-stats`
exists in all environments (issue #12).

### Owner taps "Change password" on the profile page and lands on the plan list

Known navigation bug, issue #6.

---

## Part 2 — Known issues (with evidence)

### #1 — Deleting a plan item always failed · **HIGH (feature broken)** → **RESOLVED in 0.9.0**

- **Evidence (historical):** the DELETE handler previously called `delete_item()`
  without importing it, raising `NameError` inside the handler's own `except`,
  converting it into the toast "Something went wrong. Please try again." — logged
  as `item.delete_failed`.
- **Current code:** `routes/item.py` performs a lazy import
  `from app.services.item import delete_item` **inside** the DELETE handler
  (line ~114) before calling it, so the call reaches PocketBase and deletes the
  record.
- **Impact (today):** none — the UI delete flow works. Old service-worker
  caches of `app.js` are versioned by `APP_VERSION` and purge on the next visit.
- **Fix (applied):** in-handler import; no further action needed.

### #2 — Movement category of training items is silently discarded · **MEDIUM** → **RESOLVED in 0.9.1**

- **Evidence (historical):** `modals/items_form.html` posts a required select
  `name="category"` (values Warm-up / Corrective / Main / Cardio / Cool-down),
  but neither `item_create` nor `item_update` in `routes/item.py` declared a
  `category` Form parameter, so FastAPI dropped it. The trainee dashboard
  (`pages/user/dashboard.html`) groups training items by `item.category`,
  sending un-categorized items to the "Other" bucket.
- **Current code:** both `item_create` and `item_update` declare
  `category: str = Form(None)` and include `"category": category` in the
  training payload dict (diet/steroid payloads are untouched).
- **Impact (today):** none — staff input is persisted and trainees see items
  grouped by their real category.
- **Fix (applied):** covered by the regression tests
  `test_item_create_declares_category_param`, `test_item_update_declares_category_param`,
  `test_training_payload_includes_category`, and
  `test_category_only_in_training_branch` in `tests/test_known_issue_fixes.py`.

### #3 — New accounts get a random password that is never surfaced · **UX/OPERATIONS** → **REVISED (0.9.0)**

- **Evidence:** `services/auth.py` `create_user` no longer sets
  `password = email`; it generates a random 15-character password (12 random
  alphanumeric chars + `"A1!"`), `emailVisibility=True`. **However, no UI
  template displays this initial password** — trainee/coach create flows only
  toast success and redirect.
- **Impact (old):** anyone who knew a member's email could log in; fixed.
- **Impact (new):** a brand-new user literally cannot log in — neither the new
  user nor the staff member who created the account knows the password. Staff
  must open PocketBase admin, find the user, and share/reset the password
  before the member's first login. There is no "forgot password" flow in the
  app.
- **Mitigation today:** reset the password in PocketBase admin; consider an
  invite email (PocketBase SMTP) or displaying the generated password once in
  the UI.

### #4 — Coaches read from two different sources · **LOW–MEDIUM** → **RESOLVED in 0.9.1**

- **Evidence (historical):** `GET /plans` filled its coach filter dropdown from
  `pb.collection("coaches")` (`routes/plan.py`), while everywhere else coaches
  are `users` with `role="coach"` (`services/coach.py`, plan create/edit forms,
  apply-template modal).
- **Current code:** `plan_list` now queries the `users` collection filtered by
  `tenant="..." && role="coach"`, sorted by `first_name` — the same pattern as
  the plan create/edit forms. The redundant `coaches` collection is no longer
  referenced by the app.
- **Impact (today):** none — the plan-list coach dropdown is populated from
  the same source as every other coach picker.
- **Fix (applied):** covered by `test_plan_list_filters_users_by_role_coach` in
  `tests/test_known_issue_fixes.py`.

### #5 — Session cookie sent with `Secure=False` in all environments · **HARDENING** → **RESOLVED in 0.9.0**

- **Evidence (historical):** `routes/auth.py` hardcoded `secure=False` on the
  `pb_auth` cookie.
- **Current code:** `app/security.set_auth_cookie` sets `Secure` via
  `cookie_secure_flag()` — `True` when `ENV=production` **or** the request
  arrived over https / `x-forwarded-proto: https`.
- **Impact (today):** none behind TLS; the flag is conditional now.
- **Fix (applied):** none needed; keep the reverse proxy terminating TLS and
  set `ENV=production`.

### #6 — Owner profile button "Change password" navigates wrongly · **LOW** → **RESOLVED in 0.9.1**

- **Evidence (historical):** `pages/owner/profile/profile.html` rendered
  `href="/plans/edit"` for owners; that path matches `GET /plans/{id}` with
  `id="edit"`, the plan lookup fails, and the handler redirected to `/plans`.
- **Current code:** the profile button unconditionally targets
  `/change-password` (the same target coaches/trainees had); the
  `GET /change-password` handler intentionally has no role guard, so owners can
  change their own password.
- **Impact (today):** none — no dead-end navigation; owners reach a real
  action.
- **Fix (applied):** covered by `test_profile_has_no_plans_edit_link` and
  `test_profile_links_to_change_password` in
  `tests/test_known_issue_fixes.py`.

### #7 — Version strings disagree · **TRIVIAL** → **RESOLVED in 0.9.1**

- **Evidence (historical):** `APP_VERSION = "0.9.0"` (`main.py`),
  `app/version.text` `"0.8.1"`, and `base.html` registered `/sw.js?v=0.8.1`.
- **Current code:** `APP_VERSION = "1.0.0"` (`main.py`), `app/version.text` is
  `"1.0.0"` (single source, quoted value), and `base.html` registers
  `/sw.js?v={{ app_version }}` — derived from the same `app_version` global
  already used for the CSS cache-buster.
- **Impact (today):** none — version strings are consistent and cache
  invalidation uses the same value everywhere.
- **Fix (applied):** covered by `test_app_version_matches_version_text`,
  `test_sw_register_uses_app_version`, and
  `test_no_hardcoded_old_sw_version` in `tests/test_known_issue_fixes.py`.

### #8 — Default `PB_URL` points at a shared dev database over HTTP · **OPS RISK** → **RESOLVED in 0.9.1**

- **Evidence (historical):** `app/pb.py` used
  `os.getenv("PB_URL", "http://db.dev.gyme.cloud")`.
- **Current code:** `app/pb.py` reads `PB_URL` with no default; when unset it
  fails fast with `RuntimeError("PB_URL must be set in production")` under
  `ENV=production`, otherwise it defaults to the local PocketBase
  `http://127.0.0.1:8090`. The plaintext-http-in-prod warning is retained.
- **Impact (today):** none — a misconfigured environment can no longer
  silently write to a shared dev database.
- **Fix (applied):** covered by `test_pb_url_defaults_to_localhost` and
  `test_pb_url_required_in_production` in `tests/test_known_issue_fixes.py`.

### #9 — `AGENTS.md` describes an outdated toolchain · **DOC DRIFT** → **RESOLVED in working tree**

- **Evidence (historical):** `AGENTS.md` documented `npm run css:watch` /
  `css:build` and a Tailwind CLI workflow; the actual scripts (`package.json`)
  are Vite-based (`npm run dev` / `npm run build`, config in `vite.config.js`).
  It also called `services/` an "empty placeholder".
- **Current code:** `AGENTS.md` in the working tree has been updated to match
  reality (Vite workflow, populated services, `make test`).

### #10 — Sorting mismatch in `services/item.list_items` · **LATENT** → **RESOLVED in 0.9.1**

- **Evidence (historical):** the set-literal bug (`pb.collection({collection})`)
  was fixed earlier — it passes the string correctly. The sort was still
  `+day,+order` while the item collections store their day in `seq`.
- **Current code:** `list_items` sorts by `+seq,+order` (same order used by
  `list_items_by_plan`).
- **Impact (today):** none — no route calls `list_items` directly; any future
  caller gets the correct ordering.
- **Fix (applied):** covered by `test_list_items_sorts_by_seq_order` in
  `tests/test_known_issue_fixes.py`.

### #11 — Mixed PocketBase client lifecycle · **LATENT CONCURRENCY** → **RESOLVED in 0.9.1**

- **Evidence (historical):** middleware builds a per-request client via
  `get_pb()`, but `services/auth.py` and `services/tenants.py` used
  module-level singletons whose `auth_store` is mutated during
  login/clear operations.
- **Current code:** `services/auth.login_user` now accepts an optional `pb`
  argument and falls back to `get_pb()` when none is passed;
  `load_auth_from_cookie` and `services/tenants._lookup_tenant` also use
  `get_pb()`. No module-level client remains in those services.
- **Impact (today):** none — the shared-mutable-state hazard is gone.
- **Fix (applied):** covered by `test_login_user_defaults_to_get_pb`,
  `test_auth_service_no_module_pb_singleton`, and
  `test_tenants_lookup_uses_get_pb_and_keeps_escape` in
  `tests/test_known_issue_fixes.py`.

### #12 — Debug endpoint registered in production · **MINOR EXPOSURE** → **RESOLVED in 0.9.1**

- **Evidence (historical):** `main.py` gated the `/debug` router behind
  `IS_PROD`, but `dashboard.router` — containing `GET /dashboard/debug-coach-stats`,
  a raw count dump — was included unconditionally.
- **Current code:** the `@router.get` decorator was removed from
  `debug_coach_stats`; `main.py` now registers it only inside the
  `if not IS_PROD:` block via
  `dashboard.router.add_api_route("/dashboard/debug-coach-stats", ...)` with
  `include_in_schema=False`. Production never exposes it.
- **Impact (today):** none — the endpoint is dev-only.
- **Fix (applied):** covered by `test_debug_coach_stats_has_no_route_decorator`
  and `test_debug_coach_stats_registered_only_outside_prod` in
  `tests/test_known_issue_fixes.py`.

### #13 — Comment/code drift on redirect delay · **TRIVIAL** → **RESOLVED in 0.9.1**

- **Evidence (historical):** `base.html`'s `delayed-redirect` listener waited
  `500 ms` while its comment (and route comments) promised "1.2 seconds".
- **Current code:** the listener still fires at `500 ms` and the comment now
  reads `// Gives the toast 0.5 seconds to shine before moving`. Route-level
  comments still say "1.2s" in a few spots; the actual behavior is the 500 ms
  convention.
- **Impact (today):** none — comment and code agree.
- **Fix (applied):** covered by `test_delayed_redirect_comment_matches_delay`
  in `tests/test_known_issue_fixes.py`.

### #14 — No CI or LICENSE file · **REPO HYGIENE** → **RESOLVED in 0.9.1**

- **Evidence (historical):** `tests/` existed (`tests/test_i18n.py`, a 22-test
  security regression suite at the repo root, `Makefile` `test: pytest -q`),
  but there was no `.github/workflows/` and no `LICENSE` file.
- **Current code:** `.github/workflows/ci.yml` runs `ruff check .`,
  `black --check .`, and `pytest -q` on push/PR; an ISC `LICENSE` matches the
  `package.json` `"license": "ISC"` declaration. The security regression suite
  now lives at `tests/test_security_regression.py` and the suite has grown to
  55 tests (9 i18n + 22 security + 24 known-issue-fix regressions).
- **Impact (today):** none — CI gates lint/format/tests and the project has an
  explicit license.
- **Fix (applied):** workflow + LICENSE committed; covered by
  `test_ci_workflow_checks_lint_format_and_tests` and
  `test_license_file_present` in `tests/test_known_issue_fixes.py`.

### #15 — Authenticated traffic to an unknown domain crashes · **OPS CONSTRAINT** → **RESOLVED in 0.9.1**

- **Evidence (historical):** middleware set `tenant=None` for unmatched hosts
  and only redirected unauthenticated users; role-guarded routes then
  dereferenced `request.state.tenant.id` → 500.
- **Current code:** the middleware now returns `401` (with `HX-Redirect: /login`
  for HTMX requests) or a `303` redirect to `/login` whenever `tenant is None`
  on a non-public route, before any handler runs.
- **Impact (today):** none — unknown domains no longer produce 500s for
  authenticated sessions.
- **Fix (applied):** covered by `test_middleware_tenant_none_redirect` in
  `tests/test_known_issue_fixes.py`. The deployment invariant ("every served
  hostname needs a tenants record") from doc 06 still applies.

### #16 — Deletion semantics differ between roles · **DATA LIFECYCLE** → **RESOLVED in 0.9.1**

- **Evidence (historical):** `DELETE /trainees/{id}` removed only the
  `trainees` record (`services/trainee.delete_trainee`), leaving the auth user
  able to log in with no profile; `DELETE /coaches/{id}` deletes the whole
  `users` record (`services/coach.delete_coach`).
- **Current code:** `delete_trainee` now resolves the linked `users` record
  (`trainee.user`, handling both id-string and expanded-record forms), deletes
  the `trainees` record, then cascades to `pb.collection("users").delete(...)`,
  logging `trainee_user_cascade_failed` if the user deletion fails. Both roles
  now revoke the auth account on deletion. (Plans/progress assigned to a
  deleted coach remain as dangling relations — tracked as a data-archival
  consideration, not a deletion bug.)
- **Impact (today):** none — deleted trainees can no longer authenticate.
- **Fix (applied):** covered by `test_delete_trainee_cascades_to_user` and
  `test_delete_trainee_keeps_tenant_ownership_check` in
  `tests/test_known_issue_fixes.py`.

---

## Documentation status

| | |
| --- | --- |
| Completeness | Complete for current scope (no screenshots; UI described textually) |
| Verification | Code-verified against the current working tree (version 0.9.1, 2026-09-25); live-runtime behavior and PocketBase instance settings are marked **Unverified** where applicable |
| Last verified | 2026-09-25 |
| Known conflicts resolved | Implementation preferred over `AGENTS.md` where they disagreed (issue #9, now updated); conflicts that couldn't be resolved from the repo alone (PocketBase API rules, existence of a `coaches` collection) are flagged rather than guessed |
