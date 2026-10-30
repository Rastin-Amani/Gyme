# Distribution Report — Gyme

## Project

- **Name:** Gyme
- **Repository:** https://github.com/Rastin-Amani/Gyme
- **Website:** https://gyme.cloud *(verified HTTP 200 on 2026-10-25)*
- **Version:** 0.10.0 (pre-1.0 release line; the withdrawn `v1.x` identifiers are archived in `docs/releases-withdrawn-1x.md`)
- **Latest cycle:** 2026-10-30 — DaisyUI interface rebuild, request-path speed, version line reset to 0.10.0 (see the cycle section at the end)
- **License:** ISC
- **Campaign date:** 2026-09-26
- **Mode:** AUTONOMOUS (GitHub-safe actions + permitted submissions executed directly) — earlier repo P0 phase ran under explicit user approval
- **Budget:** $0

## Executive Summary

- Opportunities discovered: 25+ candidates across GitHub, curated lists, communities, content, launch and directory platforms
- Qualified opportunities: 16
- Executed actions: 9 (6 in the approved P0 phase, 3 in this autonomous phase)
- Live results: 3 external/verified this phase (Dieterbe issue, README/CONTRIBUTING on main, Discussions enabled) — plus 6 P0 items live on GitHub
- Manual actions required: 14 destinations (screenshots, GHCR visibility, private vuln reporting, Docker Hub, Dev.to/HN/Reddit/PH/AlternativeTo/newsletters)

> Scope note: “Processed every relevant opportunity discovered and permitted during this campaign, subject to platform rules, account access, verification requirements, and free-only constraints.” Public community posting requiring human authorship (HN, Reddit, product accounts) was prepared, not executed.

## Channels Executed

| Destination | Type | Action | Status | URL / Evidence | Notes |
| --- | --- | --- | --- | --- | --- |
| Dieterbe/awesome-health-fitness-oss | curated list | Issue: add Gyme (main-list table row) | **LIVE** | https://github.com/Dieterbe/awesome-health-fitness-oss/issues/14 (open, created 2026-09-26T08:42Z) | Maintainer invites additions; Gyme absent, wger present. Rules re-checked fresh; no AI-author restriction. |
| GitHub topics | repo metadata | Typo + dup cleanup (11 topics) | **LIVE** | https://github.com/Rastin-Amani/Gyme | Removed `gym-management-ystem` typo + 6 redundant topics. |
| GitHub CI (main) | CI | Root-cause + fix, green | **LIVE** | Run 36229851866 success (head 3f43223) | `pythonpath=["."]`, CI installs `app/requirements.txt`. |
| package.json / release | versioning | Align 1.0.0 → 0.9.1; enrich v0.9.1 notes | **LIVE** | https://github.com/Rastin-Amani/Gyme/releases/tag/v0.9.1 | |
| SECURITY.md | docs | Coordinated disclosure policy | **LIVE** | commit ae2a05a | Private vuln reporting needs enabling. |
| GHCR workflow + image | package | buildx push on main + v* | **LIVE** | Run 36229851875 success; `ghcr.io/Rastin-Amani/Gyme` | ⚠️ Visibility defaults **private** → MANUAL. |
| README + CONTRIBUTING | docs | Badges, GHCR quickstart, CONTRIBUTING.md | **LIVE** | commit 394292f | CI/license/release/GHCR badges; Docker pull+run; contributions guide w/ AI-disclosure note. |
| GitHub Discussions | community | Enabled | **LIVE** | `has_discussions: true` 2026-09-26 | README links added. |

## Articles Published

| Article | Destination | URL | Purpose | Status |
| --- | --- | --- | --- | --- |
| “Multi-tenant FastAPI: one codebase, N branded gym PWAs” | Dev.to | (draft only) | architecture narrative | **MANUAL** — no Dev.to API key available (`DEVTO_API_KEY` unset); full post at `distribution/devto-article.md` |

## Community Posts

| Community | Topic/Angle | Status | URL | Notes |
| --- | --- | --- | --- | --- |
| Dieterbe list (issue) | Why Gyme belongs (multi-tenant coaching niche) | **LIVE** | issue #14 | above |
| Hacker News (Show HN) | Build story + multit-tenant tradeoffs | **MANUAL** | — | HN requires human-authored text; brief prepared in `distribution/content.md` |
| r/selfhosted | Self-hosted Trainerize/Mindbody alternative | **MANUAL** | — | Reddit requires explicit user-authorized posting; draft in `distribution/content.md`; re-check sidebar rules at post time |
| r/Python · r/FastAPI · PocketBase forum | Participation-first | **MANUAL** | — | participation-first; not yet executed |

## Directory Submissions

| Directory | Category | Status | URL | Notes |
| --- | --- | --- | --- | --- |
| awesome-selfhosted | health-and-fitness | **WAIT → 2026-10-14** | https://github.com/awesome-selfhosted/awesome-selfhosted-data | first release 2026-06-14 does not yet meet ≥4-month rule; PR must be **human-authored**; guide at `distribution/awesome-selfhosted-submission-guide.md` |
| AlternativeTo | Gym Management | **MANUAL** | — | browser flow + account; skeleton in `content.md` |
| Kludex/awesome-fastapi-projects (★1620) | FastAPI projects | **DISCOVERED** | https://github.com/Kludex/awesome-fastapi-projects | pipeline-driven (SQLite scrape), not a PR target; Gyme has `fastapi` topic → check live site later; request via issue only if absent |
| Product Hunt | Health & Fitness / Dev Tools | **MANUAL** | — | pack in `content.md`; needs screenshots; maker account |
| Indie Hackers / BetaList / LibHunt | launch/directory | **MANUAL / OPTIONAL** | — | later batch |

## Package / Registry Distribution

| Registry | Package | Version | Status | URL |
| --- | --- | --- | --- | --- |
| GHCR | ghcr.io/Rastin-Amani/Gyme | 0.9.1 / latest | **EXECUTED** (visibility pending) | https://github.com/Rastin-Amani/pkgs/container/gyme |
| Docker Hub | Gyme | — | **MANUAL** | needs Docker Hub account/org token |
| PyPI / npm | — | — | **SKIPPED** | application, not a library |

## Manual Actions Required

| Destination | Exact Blocker | Prepared Asset | Required Human Action |
| --- | --- | --- | --- |
| Screenshots / social preview | GitHub exposes no API for the social-preview image; README images are live | `docs/screenshots/dashboard.png` | Settings → General → Social preview → upload the dashboard screenshot |
| GHCR package visibility | token lacks `read:packages`; no docker CLI here | workflow + run working | Settings → Packages → Gyme → make public |
| GitHub private vulnerability reporting | disabled on repo | SECURITY.md already points at it | Repo settings → Code security → enable |
| Dev.to article | no API key | `distribution/devto-article.md` | export key (`DEVTO_API_KEY` or web editor) and publish |
| Hacker News Show HN | HN AI-text policy | fact briefing in `content.md` | write/submit as the human maintainer |
| r/selfhosted post | Reddit requires user-authorized posting | `content.md` draft | post via your account; re-read sidebar rules |
| Product Hunt | maker account + media required | launch pack in `content.md` | sign in as maker, upload screenshots, launch |
| AlternativeTo | browser + account | category mapping in `content.md` | add “software” entry, wait for approval |
| Newsletters (Python Weekly etc.) | submission forms require email/browser | one-liners in `content.md` | submit via forms |
| Docker Hub | account/org token | Dockerfile ready | create repo, add token to CI secrets, push |
| awesome-selfhosted | human-authored PR + age rule | `awesome-selfhosted-submission-guide.md` | submit PR ~2026-10-14 |
| Dieterbe list | — | issued (LIVE) | monitor #14, answer maintainer questions |
| Indie Hackers / BetaList | human account post | outline in `content.md` | optional later batch |

## Blocked / Skipped

| Destination | Reason | Revisit Date |
| --- | --- | --- |
| websearch / external net tools | HTTP 403 from this workspace | whenever network permits |
| hn.algolia / AlternativeTo / Azure logs | blocked/empty/unreachable from this network | re-check at submit time |
| awesome-selfhosted | first-release age rule (0.1.0 = 2026-06-14) | **2026-10-14** |
| PyPI / npm | not a library | never |
| Paid directories/featured listings | free-first budget $0 | skip unless user authorizes spend |
| Fake-engagement channels | prohibited | never |

## Performance

| Destination | Stars | Forks | Clones | Downloads | Signups | Notes |
| ---: | ---: | ---: | ---: | ---: | ---: | --- |
| GitHub (Rastin-Amani/Gyme) | 0 | 0 | — | — | — | baseline 0 at campaign start; measure via Insights after launch |
| GHCR image | — | — | — | 0 | — | visibility still private; no pulls expected until public |
| Dieterbe issue / other | — | — | — | — | — | no engagement yet (created today) |

## What Worked

- Root-causing and permanently fixing CI (pythonpath + requirements drift) — the single biggest launch blocker, now green with a documented why.
- Clean 11-topic set + enriched release notes + SECURITY.md + GHCR workflow + badges — the repo now looks like a launchable OSS product from the outside.
- The Dieterbe issue was created because rules were re-checked at submission time and the maintainer explicitly invites additions — a legitimate, honest, disclosed submission.
- All facts in every prepared asset trace to the repo (version 0.9.1, ISC, 55 tests, Docker, i18n list).

## What Did Not Work

- ~~Cannot produce screenshots (no runnable live instance + PocketBase in this environment)~~ Resolved 2026-10-25: seeded local PocketBase + captured 9 real screenshots — see the cycle section below.
- GHCR visibility could not be flipped programmatically (token scopes).
- Non-GitHub verification (websearch, HN Algolia, Product Hunt, AlternativeTo) is network-blocked here — every rule claim for those must be re-verified by the human at submit time.
- Creating the Dieterbe issue, while successful, intentionally excluded the maintainer's “interesting” sub-list choice — placement is up to them.

## Content Created

- `distribution/content.md` — channel-native drafts: HN brief, r/selfhosted post, PH pack, newsletter one-liners, X/LinkedIn shorts, fact-check gate.
- `distribution/devto-article.md` — complete Dev.to article (ready to publish with key/account).
- `distribution/awesome-selfhosted-submission-guide.md` — human-only checklist + YAML schema for the October PR.
- Repo: `README.md` badges + GHCR quickstart, `CONTRIBUTING.md`, `SECURITY.md`, `.github/workflows/docker-publish.yml`.
- Superseded working docs (fact-bank `strategy.md`, opportunity DB `opportunities.md`, Dieterbe issue source `dieterbe-suggestion.md`) were removed 2026-09-26; this report is the single source of truth.

## New Opportunities Discovered

- Kludex/awesome-fastapi-projects (★1620) — monitor live site for auto-inclusion.
- Discussion via GitHub Discussions (now enabled) — long-tail discovery channel for feedback/issues.
- og:image/social preview — once screenshots exist, also enables X/LinkedIn link-preview quality.

## Lessons

- CI “red but local green” here meant an import-path/environment mismatch, not flaky infrastructure — always pull the failed-step logs before concluding.
- Repo polish (badges, GHCR, SECURITY, CONTRIBUTING, clean topics) is cheap, safe, and materially changes first impressions — do it before any external submission.
- Destinations with explicit “human-authored” requirements (HN, awesome-selfhosted) must be prepared, never faked.

## Next Distribution Cycle

1. Human: upload the social preview image (dashboard screenshot) and keep README screenshots current.
2. Human: GHCR public + private vuln reporting enabled (5 minutes, unlocks image pulls and security reporting).
3. Dev.to publish (key) → cross-promote on X/LinkedIn after a few days.
4. 2026-10-14: awesome-selfhosted PR (human, per guide).
5. Continual: monitor issue #14, Discussions, and repo traffic; batch HN → r/selfhosted → PH → newsletters with rule checks before each.

## Evidence

- CI green: run 36229851866 (success), GHCR publish run 36229851875 (success).
- Release: https://github.com/Rastin-Amani/Gyme/releases/tag/v0.9.1
- Dieterbe issue accepted: https://github.com/Dieterbe/awesome-health-fitness-oss/issues/14 (`state: open`)
- Repo commits: 3f43223 (GHCR), 1ce4240 (CI deps), b9227e5 (pythonpath), ae2a05a (SECURITY.md), 394292f (README/CONTRIBUTING); discussions enabled (`has_discussions: true`).
---

## Cycle 2026-10-25 — README visuals and product-site links

**Version:** 1.4.0 · **Mode:** AUTONOMOUS · **Budget:** $0

### Executed (LIVE)

| Action | Evidence | Status |
| --- | --- | --- |
| Removed billing and restored 1.4.0 | commit `990824c` | **PUSHED** |
| Fixed Today tab init, ARIA state, plan chevrons and dashboard span | commit `af46c90` | **PUSHED** |
| Added logo + 9 real screenshots from a seeded local app | commit `fdb6e57`, `docs/assets/logo.svg`, `docs/screenshots/` | **PUSHED** |
| README rebuilt: logo, hero, TOC, why-Gyme, cloud vs self-host, compare/migrate, security, docs | commit `fdb6e57` | **PUSHED** |
| 21 unique links to `gyme.cloud/en` product pages | `README.md` | **VERIFIED 200** |
| CI + GHCR after push | [CI run 40211520620](https://github.com/Rastin-Amani/Gyme/actions/runs/40211520620) success · [GHCR run 40211520622](https://github.com/Rastin-Amani/Gyme/actions/runs/40211520622) success | **LIVE** |
| GitHub homepage → `https://gyme.cloud/en/` | `gh repo edit` 2026-10-25 | **LIVE** |
| Topics += `htmx`, `tailwindcss`, `pocketbase`, `jinja2`, `gym-software`, `fitness-coaching`, `docker` | 18 topics total | **LIVE** |

### Verification

- 55 tests pass; `ruff check .` and `black --check .` clean.
- Every `gyme.cloud` and `app.gyme.cloud` URL used in the README returned HTTP 200.
- All 9 README images exist and were captured from the running app (1280×/390× viewports, 2–3× DPR).
- Demo content is fictional: “Northline Strength”, 24 trainees, three coaches; no customer data or secrets.

### Manual follow-up

| Action | Blocker | Evidence |
| --- | --- | --- |
| Upload repository social preview | GitHub has no API for it | `docs/screenshots/dashboard.png` → Settings → General → Social preview |
| Product Hunt media | maker account | the 9 screenshots are ready to upload |
| Dev.to / article images | publishing key | use `docs/screenshots/` directly |

### Notes

- The README now opens with the product problem and two clear paths (cloud vs self-host), not a feature inventory; the technical sections remain unchanged below it.
- The screenshots surfaced four real UI defects (blank Today tab, always-selected Diet tab, backward plan chevrons, half-empty dashboard grid); all are fixed in `af46c90` rather than papered over in the images.

---

## Cycle 2026-10-30 — interface rebuild and version line reset

**Version:** 0.10.0 · **Mode:** AUTONOMOUS · **Budget:** $0

### Executed (LIVE)

| Action | Evidence | Status |
| --- | --- | --- |
| Rebuilt the interface on a single DaisyUI theme (shell, ledgers, forms, modals, auth screens) | commits `ecbb65b`–`42370d4` | **PUSHED** |
| Cut the request-path cost: pooled PocketBase client, 30 s token cache, parallel reads, gzip, immutable assets | commits `daa450f`–`0d5032f` | **PUSHED** |
| Withdrew the `v1.0.0`–`v1.7.0` tags and releases (numbering error; billing already reverted) | tags deleted on origin, notes archived in `docs/releases-withdrawn-1x.md` | **DONE** |
| Reset the release line to `v0.10.0` | commit `cbe20d3`, tag `v0.10.0`, [release](https://github.com/Rastin-Amani/Gyme/releases/tag/v0.10.0) | **LIVE** |
| CI + GHCR for the release | [CI run 41035669596](https://github.com/Rastin-Amani/Gyme/actions/runs/41035669596) success · [GHCR run 41035715759](https://github.com/Rastin-Amani/Gyme/actions/runs/41035715759) published `ghcr.io/rastin-amani/gyme:v0.10.0` | **LIVE** |
| Pruned superseded GHCR image versions | `.github/workflows/prune-packages.yml` (workflow_dispatch) | **PENDING RUN** |

### Verification

- 57 tests pass; `ruff check .` and `black --check .` clean.
- App booted against a live PocketBase: `/login` renders, `/healthz` 200, `/manifest.json` and `/sw.js` carry `0.10.0`, `/static/app.css` is served `immutable`, HTML is gzipped.
- Release identity agrees across `APP_VERSION`, `app/version.text`, `package.json`, the git tag, the GitHub release and the Docker image.

### Notes

- The 1.x numbering shipped in error: `v1.5.0`/`v1.6.0` carried a billing experiment that was reverted on `main`, and `v1.7.0` inherited the number. The project is pre-1.0, so the line resumes at `0.10.0`; no commit was rewritten and the withdrawn release notes are preserved in the repository.
- Container images published under the withdrawn tags are unsupported and are being removed from GHCR by the pruning workflow above.
