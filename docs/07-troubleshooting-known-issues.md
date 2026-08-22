# 07 — Troubleshooting & Known Issues

**Verification status:** every issue below was confirmed by reading the source
at `main` @ `657ec90` (verified 2026-08-22). File/line references are included
so each claim can be checked. Issues are numbered; other documents reference
these numbers.

---

## Part 1 — Troubleshooting by symptom

### Styles are broken / page renders unstyled

1. Check whether built assets exist: `ls app/static/app.css app/static/app.js`.
2. If you changed templates/Tailwind classes recently, rebuild: `npm run build`
   (Vite writes to `app/static`, `emptyOutDir=false`).
3. Hard-refresh once; afterwards the service worker's stale-while-revalidate
   strategy self-heals CSS/JS on the next load (see `app/static/sw.js`).

### Login shows «خطای سیستم: باشگاه یافت نشد!»

The hostname you're browsing is not any gym's domain.

1. Compare your browser URL's hostname with `tenants.domain` records.
2. Add a matching `tenants` record or browse via a mapped hostname (dev tip:
   `/etc/hosts` entry, e.g. `127.0.0.1 yourgym.local`). Evidence:
   `middleware.py` resolves tenants by Host header; `routes/auth.py` returns
   this exact toast when `request.state.tenant` is missing.

### Login fails («اطلاعات اشتباه است!») although credentials seem right

1. Confirm the account belongs to *this* gym: logins from another tenant's
   account are deliberately rejected (`login_cross_tenant_denied`,
   `services/auth.py`).
2. Check PocketBase reachability: look for `auth_refresh_failed` /
   `login_failed` warnings in app logs.
3. Remember new accounts start with **password = email** (issue #3).

### Everything errors right after a deployment

1. Verify `PB_URL` is set for the container/process — the default silently
   points at the project's dev server (`app/pb.py`, issue #8).
2. Verify PocketBase is reachable from the app host (`curl $PB_URL/api/health`
   against your instance).
3. If JSON logs show `request.error` with tenant-related tracebacks on every
   authenticated route, the serving hostname has no `tenants` record (issue
   #15).

### Creating a trainee fails

Toast «ثبت‌نام کاربر انجام نشد. (احتمالا ایمیل تکراری است یا کمتر از ۸ کاراکتر
دارد)» means the underlying `users.create` failed: duplicate email, or email
shorter than 8 characters (because the initial password equals the email,
PocketBase enforces its minimum length). Evidence: `routes/trainee.py`,
`services/auth.create_user`.

### Deleting a plan item always shows an error

Known bug, issue #1 below. The API call never reaches PocketBase. Workaround:
edit the item instead. Fix is a one-line import change.

### Trainee sees every exercise grouped under «سایر»

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

### Owner taps «ویرایش حساب» on the profile page and lands on the plan list

Known navigation bug, issue #6.

---

## Part 2 — Known issues (with evidence)

### #1 — Deleting a plan item always fails · **HIGH (feature broken)**

- **Evidence:** `app/routes/item.py` line 3 imports only
  `list_items, get_item_by_id, create_item, update_item`; the DELETE handler
  (line 79) calls `delete_item(...)`. The function exists in
  `app/services/item.py` (`delete_item`, last function) but was never
  imported. At runtime this raises `NameError`, which the handler's own
  `except` catches and converts into the toast «مشکلی پیش آمد. لطفا دوباره
  تلاش کنید.» — logged as `item.delete_failed`.
- **Impact:** users cannot delete training/diet/steroid items through the UI;
  orphaned items can only be removed directly in PocketBase.
- **Fix:** extend the import to
  `from app.services.item import list_items, get_item_by_id, create_item, update_item, delete_item`.

### #2 — Movement category of training items is silently discarded · **MEDIUM**

- **Evidence:** `modals/items_form.html` posts a required select
  `name="category"` (values گرم کردن / حرکات اصلاحی / اصلی / هوازی / سرد کردن),
  but neither `item_create` nor `item_update` in `routes/item.py` declares a
  `category` Form parameter, so FastAPI drops it. The trainee dashboard
  (`pages/user/dashboard.html`) groups training items by `item.category`,
  sending un-categorized items to the «سایر» bucket.
- **Impact:** staff input is lost; trainees see flat lists under «سایر».
- **Fix:** add `category: str = Form(None)` to both handlers and include
  `"category"` in the training payload dict.

### #3 — New accounts start with password = email address · **SECURITY/UX**

- **Evidence:** `services/auth.py` `create_user`: `password: email`,
  `passwordConfirm: email`.
- **Impact:** anyone who learns/guesses a member's email can log in until the
  password is changed; also couples password policy to email format (≥8 chars).
- **Mitigation today:** instruct every new user to rotate immediately
  (documented prominently in the user guide); consider generating a random
  one-time password or an invite flow instead.

### #4 — Coaches read from two different sources · **LOW–MEDIUM**

- **Evidence:** `GET /plans` fills its coach filter dropdown from
  `pb.collection("coaches")` (`routes/plan.py`, try/except around lines 61–75),
  while everywhere else coaches are `users` with `role="coach"`
  (`services/coach.py`, plan create/edit forms, apply-template modal).
- **Impact:** if no `coaches` collection exists (the rest of the codebase
  doesn't require one), the plan-list filter dropdown is simply empty
  (exception swallowed → `coaches = []`).
- **Fix:** switch that query to `users` filtered by `role="coach"` like the
  other forms, or drop the redundant collection.

### #5 — Session cookie sent with `Secure=False` in all environments · **HARDENING**

- **Evidence:** both `set_cookie(pb_auth …)` calls in `routes/auth.py` hardcode
  `secure=False`; comments acknowledge production should flip it, but nothing
  reads `ENV` here.
- **Impact:** browsers will transmit the session cookie over plain HTTP if any
  non-HTTPS origin/route is exposed.
- **Fix:** `secure=os.getenv("ENV") == "production"` (or always True behind a
  TLS-terminating proxy).

### #6 — Owner profile button «ویرایش حساب» navigates wrongly · **LOW**

- **Evidence:** `pages/owner/profile/profile.html` renders
  `href="/plans/edit"` for owners; that path matches `GET /plans/{id}` with
  `id="edit"`, the plan lookup fails, and the handler redirects to `/plans`.
- **Impact:** dead-end navigation; owners cannot edit their own account from
  the UI (only password change exists for coaches/trainees).
- **Fix:** point owners to a real account-edit target (currently none exists)
  or hide the button.

### #7 — Version strings disagree · **TRIVIAL**

- **Evidence:** `APP_VERSION = "0.8.0"` (`main.py`), `app/version.text`
  `"0.8.0"`, but `base.html` registers `/sw.js?v=0.8.1`.
- **Impact:** cosmetic; runtime cache versioning correctly uses `APP_VERSION`.
- **Fix:** derive the query param from `templates.env.globals["app_version"]`.

### #8 — Default `PB_URL` points at a shared dev database over HTTP · **OPS RISK**

- **Evidence:** `app/pb.py`: `os.getenv("PB_URL", "http://db.dev.gyme.cloud")`.
- **Impact:** any environment that forgets the variable silently uses the
  project's dev PocketBase — data goes to the wrong place over plaintext HTTP.
- **Fix:** make startup fail fast when `PB_URL` is unset in production, and/or
  change the default to localhost.

### #9 — `AGENTS.md` describes an outdated toolchain · **DOC DRIFT**

- **Evidence:** `AGENTS.md` documents `npm run css:watch` / `css:build` and a
  Tailwind CLI workflow; the actual scripts (`package.json`) are Vite-based
  (`npm run dev` / `npm run build`, config in `vite.config.js`). It also calls
  `services/` an "empty placeholder"; the layer is now fully populated.
- **Impact:** contributors following it will hit missing npm scripts.
- **Fix:** update AGENTS.md commands section (this docs set already reflects
  reality).

### #10 — Dead/broken helper `list_items` in `services/item.py` · **LATENT**

- **Evidence:** `pb.collection({collection})` passes a Python **set literal**
  instead of the string, and sorts by `+day,+order` although item collections
  use `seq`/`order`. No route currently calls it (they use
  `list_items_by_plan` / `get_items_by_plan_seq`), so nothing breaks today.
- **Fix:** delete it or correct to `pb.collection(collection)` +
  `"+seq,+order"` before anyone reuses it.

### #11 — Mixed PocketBase client lifecycle · **LATENT CONCURRENCY**

- **Evidence:** middleware builds a per-request client via `get_pb()`, but
  `services/auth.py` and `services/tenants.py` use module-level singletons
  whose `auth_store` is mutated during login/clear operations.
- **Impact:** today's flows don't depend on store state afterwards, but
  concurrent requests share that mutable state — a hazard if reused more
  widely.
- **Fix:** standardize on `get_pb()` per request/unit-of-work.

### #12 — Debug endpoint registered in production · **MINOR EXPOSURE**

- **Evidence:** `main.py` gates the `/debug` router behind `IS_PROD`, but
  `dashboard.router` — containing `GET /dashboard/debug-coach-stats`, a raw
  count dump — is included unconditionally.
- **Impact:** authenticated members can hit a debugging endpoint in
  production; information exposure is limited to aggregate counts.
- **Fix:** move it behind the same gate or delete it.

### #13 — Comment/code drift on redirect delay · **TRIVIAL**

- **Evidence:** `base.html`'s `delayed-redirect` listener waits `500 ms` while
  its comment (and several route comments) promise "1.2 seconds".
- **Fix:** align comment or timing.

### #14 — No tests, CI, or LICENSE file · **REPO HYGIENE**

- **Evidence:** repository contains no `tests/`, `.github/workflows/`, or
  `LICENSE`. `package.json` carries `"license": "ISC"` metadata only, which
  does not establish project licensing for the codebase.
- **Recommendation:** add a minimal pytest smoke suite (route table, template
  rendering with a fake PB client), CI running `ruff`/`black --check`, and a
  LICENSE decision.

### #15 — Authenticated traffic to an unknown domain crashes · **OPS CONSTRAINT**

- **Evidence:** middleware sets `tenant=None` for unmatched hosts and only
  redirects unauthenticated users; role-guarded routes then dereference
  `request.state.tenant.id` (e.g. `routes/dashboard.py` first lines) → 500.
- **Impact:** harmless if DNS/hostnames are managed correctly; noisy failures
  otherwise.
- **Mitigation:** treat "every served hostname needs a tenants record" as a
  deployment invariant (checklist in doc 06); optionally redirect to `/login`
  with the system-error toast when tenant is None.

### #16 — Deletion semantics differ between roles · **DATA LIFECYCLE**

- **Evidence:** `DELETE /trainees/{id}` removes only the `trainees` record
  (`services/trainee.delete_trainee`), leaving the auth user able to log in
  with no profile; `DELETE /coaches/{id}` deletes the whole `users` record
  (`services/coach.delete_coach`), revoking access but leaving their plans
  assigned to a dangling relation.
- **Impact:** inconsistent lifecycle; decide intended behavior (cascade,
  anonymize, or deactivate) and implement consistently.

---

## Documentation status

| | |
| --- | --- |
| Completeness | Complete for current scope (no screenshots; UI described textually) |
| Verification | Code-verified against `main` @ `657ec90`; live-runtime behavior and PocketBase instance settings are marked **Unverified** where applicable |
| Last verified | 2026-08-22 |
| Known conflicts resolved | Implementation preferred over `AGENTS.md` where they disagreed (issue #9); conflicts that couldn't be resolved from the repo alone (PocketBase API rules, existence of a `coaches` collection) are flagged rather than guessed |
