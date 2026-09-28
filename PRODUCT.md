# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Primary: gym owners and coaches running a small gym — they manage trainees, build training/diet/medication plans from reusable templates, and log body-metric progress with photos. Secondary: trainees on their phones following the "Today" slice of each plan and tapping Done daily. All authenticated, multilingual (en default + es/tr/hy), mobile-first PWA installed per gym.

## Product Purpose

Multi-tenant gym coaching platform: each gym gets its own branded installable web app where staff deliver plans and trainees execute them daily. Success = coach creates plan in minutes, trainee understands today's work in seconds and marks Done without friction.

## Positioning

Hostname-resolved tenant gyms with per-gym branding, PWA install, and server-rendered HTMX continuity (persistent shell, granular swaps) — not a generic fitness SaaS dashboard.

## Operating Context

Coaches work on desktop/mobile between sessions; trainees check phones at the gym or kitchen. Workflows: trainee list/search/filter → trainee detail → plans/items → progress logs; trainee Today tabs (diet/training/steroid) → Done. Offline banner + service worker cache; PocketBase backend (tenants, users, trainees, plans, items, progress_logs).

## Capabilities and Constraints

Routes: /dashboard, /trainees(+/new, /search, /filter), /plans(+templates), /coaches, /profile, /user/dashboard, /user/plans, /user/profile, /login, /locale. HTMX partial swaps into #page-content with hx-push-url; Alpine store `ui` owns sidebar/modal/tab/toast only — backend is source of truth. Constraints: UI/UX-only redesign; no Alpine changes; no new stack deps (DaisyUI + Tailwind + existing motion/mini only); no zoom/scale-up hover effects; preserve all hx-*, form names, i18n msgids, PocketBase contracts.

## Brand Commitments

Slate Pine: "calm paper, deep pine". Canvas #FAFAF8/#F1F0EB, hairline #E4E2DA, ink #1A1E1C, pine #1C4A3C (only actionable color — owns CTAs, active states, focus, selection), stone #57534E secondary, moss #A3B18A accent used sparingly. System sans display 700/800 tight tracking (no webfont fetch). Flat: 1px hairlines, 12/16px radii, no shadows/gradients/glass, no pills except avatar/status/toggle. Hairline ledger rows, KPI strip, segmented pine tab rail. (Supersedes Caldera Evolved — see `docs/retheme-slate-pine.md`.)

## Evidence on Hand

Live templates under app/templates (base, layouts/dashboard, owner dashboard/trainees/plans/coaches/profile, user Today/plans/profile, login). Design tokens in app/static/main.css. No new copy claims; demonstration data stays synthetic.

## Product Principles

1. Today-clarity first: the trainee's next action is visible in seconds.
2. Server truth, instant feedback: every tap answers locally, settles from server.
3. Flat forge: hierarchy from surface contrast and type, never shadows or zoom.
4. One accent, one job: ember means actionable; everything else stays calm.
5. Thumb-first: 44px targets, sticky actions, safe-area dock on every screen.

## Accessibility & Inclusion

WCAG AA contrast (fog #6a6964 on limestone), visible ember focus rings, semantic tabs/lists/forms, keyboard-operable dock and modals, prefers-reduced-motion collapse, LTR-only locales.
