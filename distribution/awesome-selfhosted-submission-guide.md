# Gyme — awesome-selfhosted submission guide (HUMAN-authored)

> **Why this is here:** awesome-selfhosted now stores entries in
> `awesome-selfhosted/awesome-selfhosted-data` and its CONTRIBUTING.md states
> that AI agents must NOT create/submit PRs or write entry text on a person's
> behalf — and the PR template includes a "submission was done by a human, not
> a machine/LLM" attestation that only a human can truthfully make.
> This file therefore contains a **checklist and schema reference only**.
> The entry text and the PR must be written and submitted by you (the maintainer).

## Objective eligibility (checked 2026-09-26)

| Requirement | Status | Evidence |
| --- | --- | --- |
| Self-hostable | ✅ | Dockerfile + docs/06-configuration-deployment.md |
| Actively maintained | ✅ | Commits+releases through 2026-09-25 |
| Working install instructions | ✅ | README quick start + docs/02 + docs/06 |
| Not already listed | ✅ | Not present in README / data repo |
| **First release ≥ 4 months old** | ❌ WAIT | v0.1.0 tagged 2026-06-14 → eligible ~**2026-10-14** |

**Action:** wait, then submit in mid-October 2026. Do not submit early; the
maintainers enforce the age rule.

## How to submit (steps for you, the human)

1. Go to https://github.com/awesome-selfhosted/awesome-selfhosted-data
2. Read `CONTRIBUTING.md` and the PR template (`.github/PULL_REQUEST_TEMPLATE.md`).
3. Add a new file `software/gyme.yml` (kebab-case, one project per file) via the
   GitHub web UI ("Create new file" → "Create a new branch for this commit and
   start a pull request" → "Create pull request").
4. Base the YAML on `.github/ISSUE_TEMPLATES/addition.md` (the template) and an
   existing entry for field shapes (e.g. `software/wger.yml`).

## Field guidance (schema reference — you write the values)

```yaml
name: Gyme
website_url: https://gyme.cloud            # or repo if site unreachable
source_code_url: https://github.com/Rastin-Amani/Gyme
description: >-
  # keep < ~200 chars; no "open-source"/"self-hosted" (implied by the list);
  # no "$PROJECT is a ..." opener; concrete nouns, e.g.:
  "Multi-tenant gym management and coaching platform — per-gym branded PWA,
  trainee/coach roles, training/nutrition/supplement plans, progress tracking
  with body-metric calculations (alternative to Trainerize, Mindbody)."
  # LANGUAGE NOTE (matches the current product — 2026-09): Gyme's UI is
  # English-first; es/tr/hy gettext catalogs exist and every locale renders
  # left-to-right with Gregorian dates. Do NOT claim Persian/RTL/Jalali support —
  # those were removed from the product.
licenses:
  - ISC                          # SPDX identifier already known to the data repo
tags:
  - health-and-fitness           # existing tag (verified in tags/)
platforms:
  - Docker                       # Python is a runtime, Docker is the ship artifact
demo_url: (if a public demo exists — verify first)
related_software_url:            # optional: local name like wger if desired
```

Rules to respect (from CONTRIBUTING.md):
- Remove comments and unused optional fields when finalizing.
- Commit message like `add Gyme`; descriptive, not generic.
- In single-page mode the software appears only under its **first** tag — so
  keep `health-and-fitness` first.
- Description must not contain words like "open-source", "free", "self-hosted"
  (they are implied by the list).
- If claiming "alternative to X, Y", only use services where that is honest
  (Trainerize/Mindbody are commercial coaching platforms Gyme replaces).

## How I can still help (within the rules)

- Review your drafted `.yml` before you submit (field names, kebab-case, tag
  validity, SPDX `ISC`).
- Double-check eligibility dates and dead-link checks.
- Point you at the templates: CONTRIBUTING.md, `.github/ISSUE_TEMPLATES/addition.md`,
  and the PR template.