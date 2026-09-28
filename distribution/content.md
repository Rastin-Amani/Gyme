# Gyme — Prepared Content (channel-native drafts)

> Each draft targets one channel's context. Do NOT reuse the same body elsewhere.
> All public posts remain **drafts until approved**; HN and Reddit final text must be authored/edited by the human.

---

## 1) Dev.to / Hashnode — architecture article (HIGH fit)

**Working title:** One gym-coaching platform, branded per gym

**Outline (problem → approach → tradeoffs → result):**
1. **Problem:** every gym asked for "an app", but one deployed app per gym didn't scale; coaches wanted per-trainee plans, not PDFs.
2. **Approach:** hostname-based tenancy (`Host` header → PocketBase `tenants`), per-tenant theme/logo/manifest, roles scoped to tenants.
3. **The stack:** SvelteKit/Svelte 5 SSR frontend with TypeScript; FastAPI owns the JSON API, authorization, and PocketBase access; Tailwind/Caldera styles; tenant-aware PWA; separate Svelte dictionaries and backend gettext (en/es/tr/hy, all LTR).
4. **Tradeoffs:** trust boundary is the `Host` header (tenant resolution + auth cookie validation via PocketBase `auth_refresh`); external DB (PocketBase) instead of ORM — no migration layer; no `dotenv` auto-loading (explicit `PB_URL`); Swagger/docs gated in prod.
5. **Result:** per-gym branded installable app from one two-service Compose deployment; open source (ISC), self-hostable with Docker; Node serves SvelteKit SSR and FastAPI stays private behind the frontend.
6. **CTA:** link to repo, docs, Dockerfile; mention gyme.cloud hosted option in one sentence.

**Disclosure:** "I built this — happy to answer questions about the tenancy model."

---

## 2) Hacker News — Show HN brief (HIGH fit; HUMAN writes final text per HN guidelines)

**Facts to verify before posting:** live demo/URL; version; license; install path.

**Suggested framing (the author's own words, not a script):**
- Point 1: built Gyme because gyms in [region] still run coaching through WhatsApp/PDF; each gym wanted *its own* branded app.
- Point 2: the interesting engineering bit is hostname-based multi-tenancy + a dynamic per-gym PWA manifest, with PocketBase as the data layer and SvelteKit SSR/forms in front of a private FastAPI JSON API.
- Point 3: honest tradeoffs list: random 15-character passwords are never shown in the UI (staff set/reset through PocketBase admin), login is limited to 5 attempts per 5 minutes per IP/identity/tenant, and PocketBase rules must be configured by the operator.
- Point 4: verify the current release and roadmap before posting; the UI supports en/es/tr/hy, all LTR.
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
> metrics. Stack: SvelteKit + FastAPI + PocketBase, ships as a two-service
> Compose deployment. UI is
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
"Gyme: multi-tenant gym-coaching platform with SvelteKit, FastAPI, and PocketBase — per-gym branded PWAs, i18n (en/es/tr/hy), Docker Compose deploy. https://github.com/Rastin-Amani/Gyme"

**Self-hosted newsletter (editorial; verify open/paid):**
"Self-hosted gym management with per-gym branded PWA, trainee/coach roles, plan templates and progress tracking. ISC, FastAPI, Docker."

---

## 6) X / LinkedIn (post-launch, channel-native shorts)

- **X:** "Ship one FastAPI app; every gym gets its own branded PWA: that's the multi-tenancy model behind Gyme (host-header → tenant → manifest). Open source, ISC. github.com/Rastin-Amani/Gyme" + screenshot.
- **LinkedIn:** problem → lesson → project: "Gyms were running coaching through WhatsApp; each wanted its own app. Building one deployable FastAPI app with hostname-based tenancy instead of N deployments — here's what that looks like in production. Open source Gyme."

---

## Content factual check (before any publication)

[ ] Recheck current version, license, test result, and CI status before posting
[ ] gyme.cloud reachable & screenshots exist (not yet)
[ ] No fabricated metrics, users, testimonials, or roadmap items
