# Gyme — Prepared Content (channel-native drafts)

> Each draft targets one channel's context. Do NOT reuse the same body elsewhere.
> All public posts remain **drafts until approved**; HN and Reddit final text must be authored/edited by the human.

---

## 1) Dev.to / Hashnode — architecture article (HIGH fit)

**Working title:** Multi-tenant FastAPI: one codebase, N branded gym PWAs

**Outline (problem → approach → tradeoffs → result):**
1. **Problem:** every gym asked for "an app", but one deployed app per gym didn't scale; coaches wanted per-trainee plans, not PDFs.
2. **Approach:** hostname-based tenancy (`Host` header → PocketBase `tenants`), per-tenant theme/logo/manifest, roles scoped to tenants.
3. **The stack:** FastAPI routers thin, services own PocketBase queries; HTML over the wire with HTMX + Alpine; Tailwind/daisyUI; PWA/service worker per tenant; i18n (gettext; en/es/tr/hy, all LTR).
4. **Tradeoffs:** trust boundary is the `Host` header (tenant resolution + auth cookie validation via PocketBase `auth_refresh`); external DB (PocketBase) instead of ORM — no migration layer; no `dotenv` auto-loading (explicit `PB_URL`); Swagger/docs gated in prod.
5. **Result:** ISO-ish per-gym branded installable app from one FastAPI app; open source (ISC), self-hostable via Docker; Docker layer excludes Node — assets pre-built with Vite.
6. **CTA:** link to repo, docs, Dockerfile; mention gyme.cloud hosted option in one sentence.

**Disclosure:** "I built this — happy to answer questions about the tenancy model."

---

## 2) Hacker News — Show HN brief (HIGH fit; HUMAN writes final text per HN guidelines)

**Facts to verify before posting:** live demo/URL; version; license; install path.

**Suggested framing (the author's own words, not a script):**
- Point 1: built Gyme because gyms in [region] still run coaching through WhatsApp/PDF; each gym wanted *its own* branded app.
- Point 2: the interesting engineering bit is hostname-based multi-tenancy + a dynamic per-gym PWA manifest, with PocketBase as the data layer and HTML-over-the-wire (HTMX) for interactivity.
- Point 3: honest tradeoffs list (see DISTRIBUTION-REPORT.md): random 15-char passwords never shown in the UI (staff reset via PocketBase admin), login rate-limited 5 attempts/5 min, no formal Contributing process yet.
- Point 4: release/roadmap (v0.9.1; multilingual en/es/tr/hy, all LTR).
- Link: https://github.com/Rastin-Amani/Gyme

**Do NOT:** ask for upvotes, coordinate comments, post AI-generated body.

---

## 3) r/selfhosted — share draft (HIGH fit; verify subreddit rules first)

**Angle:** self-hosting a Trainerize/Mindbody alternative for your own gym.

Draft body (to be rewritten by author, disclosure first line):

> We self-host our gym's app with this: an open-source (ISC) multi-tenant gym
> coaching platform. Each tenant (gym) gets its own branded PWA on its own
> domain — trainees get a "today" plan view with a Done button, coaches manage
> trainees and plans, progress logs compute BMI/BFP/BMR/TDEE/LBM/WHR from body
> metrics. Stack: FastAPI + HTMX + PocketBase, ships in a Dockerfile. UI is
> multilingual (en/es/tr/hy, all LTR). I'm the author — happy to
> answer setup questions.
> https://github.com/Rastin-Amani/Gyme

**Rule note:** this subreddit gates self-promotion; check current sidebar rules and the "self-promotion" policy before posting. Disclose authorship. Do not ask for upvotes.

---

## 4) Product Hunt launch pack (MEDIUM fit; human account; verify gyme.cloud live first)

- **Name:** Gyme
- **Tagline:** The self-hosted, multi-tenant gym coaching platform — every gym gets its own branded app.
- **Topics:** Developer Tools · Health & Fitness · Open Source
- **Description (structure, human-written):** What it is (per-gym branded PWA: trainees, plans, progress) · who it's for (gym owners/coaches; self-hosters) · key differentiator (multi-tenant + 4 languages en/es/tr/hy) · open-source ISC and self-hostable, managed option at gyme.cloud.
- **First comment:** why it was built (WhatsApp/PDF → structured plans), stack, and ask-for-feedback line.
- **Media:** screenshots + demo GIF (must be real captures — none exist yet).
- **Do NOT:** invent users/testimonials/traction.

---

## 5) Newsletter one-liners (MEDIUM fit)

**Python Weekly / PyCoder's Weekly (suggestion form):**
"Gyme: multi-tenant gym-coaching platform in FastAPI — per-gym branded PWAs, HTMX front end, PocketBase data layer, i18n (en/es/tr/hy), Docker deploy. https://github.com/Rastin-Amani/Gyme"

**Self-hosted newsletter (editorial; verify open/paid):**
"Self-hosted gym management with per-gym branded PWA, trainee/coach roles, plan templates and progress tracking. ISC, FastAPI, Docker."

---

## 6) X / LinkedIn (post-launch, channel-native shorts)

- **X:** "Ship one FastAPI app; every gym gets its own branded PWA: that's the multi-tenancy model behind Gyme (host-header → tenant → manifest). Open source, ISC. github.com/Rastin-Amani/Gyme" + screenshot.
- **LinkedIn:** problem → lesson → project: "Gyms were running coaching through WhatsApp; each wanted its own app. Building one deployable FastAPI app with hostname-based tenancy instead of N deployments — here's what that looks like in production. Open source Gyme."

---

## Content factual check (before any publication)

[ ] Version 0.9.1 · ISC license · 55 passing tests locally
[ ] CI green on main (ruff, black, pytest) — ready to link from anywhere (run 36229851866)
[ ] gyme.cloud reachable & screenshots exist (not yet)
[ ] No fabricated metrics, users, testimonials, or roadmap items