# 01 — Product Overview

**Verification status:** written against the current implementation (app version
0.9.1, `main` branch). All features described here are traceable to code in this
repository; where behavior depends on data configured in the external PocketBase
instance, that is called out explicitly.

---

## What is Gyme?

Gyme is a **multi-tenant gym coaching platform** delivered as a mobile-first
installable web app (PWA). Each gym ("tenant") gets its own branded instance of
the app on its own domain. Inside a gym:

- The **owner** and **coaches** manage trainees, build personalized programs,
  track body-metric assessments, and monitor progress from one dashboard.
- **Trainees** install the gym's app on their phone and follow their daily
  training, nutrition, and supplement plan with a single "Done" action per day.

The user interface is **multilingual**: English is the default language, and
Spanish, Turkish, and Armenian are also available. Visitors switch language with
a selector in the header; the choice is stored in a `locale` cookie. Every
locale is left-to-right, and dates render in the Gregorian calendar (Babel
medium format).

## Who it is for

| Persona | What they do in Gyme |
| --- | --- |
| Gym owner | Runs the gym's app: manages coaches and trainees, oversees all plans and statistics, sees tenant settings |
| Coach | Manages only their own trainees and their plans; records assessments |
| Trainee | Follows daily plans, views own profile — read-only consumer of plans |

## The problems it solves

- Replaces ad-hoc delivery of workout/nutrition programs via WhatsApp and PDF
  files with a structured per-trainee plan system.
- Gives each gym an app under its own brand — logo, theme colors, name, icon,
  and splash screen are driven by the gym's tenant record.
- Standardizes initial fitness assessments with automatic BMI / body-fat / BMR /
  TDEE calculations and before/after photo storage.
- Lets trainees see exactly *today's* portion of every program instead of
  reading a full multi-week spreadsheet.

## Major capabilities

### Multi-tenancy & branding

- Every request is mapped to a gym by hostname; each hostname corresponds to a
  record in the `tenants` collection.
- The marketing site is a separate application; every tenant host redirects `/`
  straight to login or dashboard.
- Per-gym branding: name, logo (used for header, favicon, PWA icons, and iOS
  splash screen), theme (`gyme`, `light`, or `custom` with custom CSS color
  variables stored on the tenant).

### Accounts & roles

- No self-signup: staff create accounts for coaches and trainees inside the app.
- Three roles: `owner`, `coach`, `trainee`. Coaches are scoped to the trainees
  and plans assigned to them; owners see everything in their gym.
- Users sign in with email + password. Passwords can be changed in-app:
  the new password must be 8–72 characters and not similar to the email address.
- Login is tenant-checked: an account belonging to another gym cannot be used,
  even if the credentials are correct.
- Login attempts are rate-limited per IP + identity + tenant (5 attempts per
  5 minutes); exceeding the limit returns `429` with a toast.

> ⚠️ **Important operational fact:** when staff create a new account, the app
> generates a **random 15-character password** (verified in `services/auth.py`).
> The UI does **not** display this password anywhere, so the staff member who
> creates the account cannot hand it to the user. A new user can only log in
> after staff resets the password through the PocketBase admin (or the account
> owner resets it for them). There is no self-service "forgot password" flow.

### Trainee management

- Paginated list (5 per page) with free-text search across name/phone/email and
  filters for gender, status, and birthdate range.
- Rich trainee profile: contact info, gender, birthdate, blood type, training
  history, steroid history, supplement history, physical limitations, notes.
- Creating a trainee walks staff through two steps: create the account, then
  fill the initial assessment (progress log) — the app navigates there
  automatically after registration.

### Plans and items

Plans come in three types, each with its own item structure:

| Plan type | Item fields |
| --- | --- |
| Training | Exercise name (autocomplete from an English exercise dataset), movement category (warm-up/main/etc.), day number, order, sets, reps, weight, rest seconds, notes |
| Diet | Meal name (Fasting, Breakfast, Snack, Pre-workout, Post-workout, Lunch, Dinner), food name (autocomplete from an English food dataset), quantity/unit, day, order, notes |
| Steroid/supplement | Name, type (Supplement/Steroid), dosage, frequency, day, order, notes |

- Exercise and food name suggestions are served from English datasets bundled in
  `data/*.csv`.
- Plans have start/end dates, days-per-week, status (active/inactive/draft), a
  responsible coach, and notes.
- **Templates:** any plan can be saved as a reusable template (with its own
  template name). Applying a template to a trainee copies the plan *and all of
  its items* into a fresh active plan for that trainee.

### Progress logs (assessments)

- Records height, weight, chest/waist/hip/arm circumferences, plus computed
  metrics: BMI, body-fat percentage, lean body mass, fat mass, BMR
  (Mifflin-St Jeor), TDEE (from an activity-level selector), and waist-to-hip
  ratio — calculated live in the browser as staff type.
- Accepts up to **5 photos**, max **5 MB** each (JPEG/PNG/WebP/GIF), with
  preview and client-side validation.
- Saving a log also updates the trainee's current height/weight. Logs can be
  edited later; they are shown on the trainee detail page newest-first.

### Dashboards

- **Owner dashboard:** counters for active/inactive trainees and per-type plan
  counts, filterable to this week/month/all time; a per-coach breakdown showing
  plan totals, active plans, plans currently in progress, and distinct trainees.
- **Trainee "Today" dashboard:** tabs for Diet (nutrition), Training,
  Steroid — only tabs with plans appear. Each plan card shows today's
  items grouped by meal or exercise category and a **Done** button that
  advances the plan to its next day (wrapping around at the end). A warning
  banner reminds trainees to press it every day.

### Installable app (PWA)

- Dynamic web-app manifest per gym (name, icons generated from the gym logo,
  standalone portrait mode, dark background).
- Service worker caching strategy: instant-from-cache static assets with
  background refresh, cache-first images (including photos served by
  PocketBase), network-first pages falling back to the last visited copy or a
  built-in offline page.
- An offline banner appears whenever the device loses connectivity.
- On iOS, first-time visitors get a step-by-step "Add to Home Screen" overlay;
  a branded splash screen is generated on the fly from the gym logo/colors.

## What Gyme deliberately does *not* do today

Stated so readers don't assume otherwise:

- No payments, billing, or subscription management (payment tracking is only
  mentioned as a pain point on the separate marketing site).
- No trainee-facing editing: trainees cannot mark individual items done, chat,
  or upload anything; their action set is view + daily "Done".
- No notifications/push messaging, no scheduling/calendar beyond plan dates.
- No self-service signup or password recovery; account lifecycle runs through
  gym staff (or direct database administration). Because the app generates
  random initial passwords and never displays them, new accounts must have
  their password reset via PocketBase admin before first login.
- No CI configuration or LICENSE file; automated tests do ship under `tests/`
  (`test_i18n.py` and the security regression suite).

## Requirements in brief

- A running [PocketBase](https://pocketbase.io) instance acting as database,
  authentication provider, and file store. The collections the code expects are
  listed in [06-configuration-deployment.md](06-configuration-deployment.md);
  the schema itself lives in PocketBase (no migrations are in this repo).
- One `tenants` record per gym domain, plus the required collections, must be
  provisioned before the app is usable.
- Python 3.11+ runtime and (for development/rebuilds only) Node.js.

See [02-getting-started.md](02-getting-started.md) for setup and
[04-architecture.md](04-architecture.md) for the technical deep dive.
