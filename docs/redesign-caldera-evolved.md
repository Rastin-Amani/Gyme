# Caldera Evolved — redesign notes

UI/UX-only pass. No Alpine changes (`app/static/main.js` untouched),
no new npm deps, no routes/forms/HTMX logic changes, all `hx-*`,
`x-data`/`@click`/`:class`/`$store`, form names and `_()` msgids preserved.

## What changed

- `app/static/main.css` — same Caldera tokens; added: sticky blurred
  `.app-header`, `.seal` sulfur tags, `.ledger-row` wash + chevron nudge,
  `.seal-avatar` status dot, `.today-rail` ember pill tabs, `.item-card`
  hover lift, `.btn-arrow` nudge, toast/modal keyframes, skeleton shimmer,
  themed selection/focus/scrollbar/caret, `halftone-drift` (position-only,
  no zoom), full `prefers-reduced-motion` collapse.
- `layouts/dashboard.html` — sticky header, semibold truncated title,
  gym-name pill seal, dock with 44px targets + ember active dot + safe-area.
- `owner/dashboard.html` — emoji heading → Anton + `Gym pulse` sulfur seal.
- `dashboard_stats.html` — halftone hero chamber with count-up numerals +
  ledger plan rows with drawn SVG seals (was emoji stat cards).
- `dashboard_content.html` / `coach_stats.html` — ember SVG headers,
  tabular numerals, neutral summary pill, dashed empty chamber.
- `trainees.html` — ember-wash avatars with status dot, ledger rows,
  arrow CTA on New trainee, count seal.
- `user/dashboard.html` — halftone Today hero, segmented ember-pill rail
  (no emoji), sulfur meal/block seals, big ember Done CTA with arrow,
  item-card micro-motion, unified quantity pills, emoji-free empties.
- `login.html` — drifting halftone hero, arrow CTA (structure untouched).
- `PRODUCT.md` / `DESIGN.md` — product truth + evolved-Caldera contract.

## Constraints honored

- Zero zoom/scale-up hovers (press compress ≤0.97 only, hover = translate).
- DaisyUI + Tailwind + existing `motion/mini` only; nothing added.
- `npm run build` via Vite passes (`app/static/app.css` rebuilt).
- Jinja parse: my 9 edited templates parse clean; the 2 `{% with %}`
  errors in untouched `forms/*` are pre-existing (custom env in
  `app/templates.py`).
- `pytest` could not run here (no venv, system pip blocked by PEP 668);
  run `make test` in your own env before shipping.
