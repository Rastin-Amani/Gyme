# Retheme — Slate Pine (replaces Caldera Evolved)

One-line rationale: Caldera Evolved burned eyes — `#fc5000` ember everywhere, `#524ae9` violet halftone hero, `#f5f28e` sulfur seals, 2px `#070607` borders on everything, 800px pill radii, Anton display. Slate Pine replaces it wholesale with a calm, low-saturation, premium gym SaaS theme.

## Tokens (single DaisyUI theme `gyme`, light)

| Role | Value |
|---|---|
| base-100 / paper | `#FAFAF8` |
| base-200 / canvas | `#F1F0EB` |
| base-300 / hairline | `#E4E2DA` |
| base-content / ink | `#1A1E1C` |
| primary / pine | `#1C4A3C` (content `#FFFFFF`) |
| secondary / stone | `#57534E` |
| accent / moss | `#A3B18A` (sparingly: tiny badges/status only) |
| info / success / warning / error | `#0E7490` / `#15803D` / `#B45309` / `#B91C1C` |
| fog (meta text) | `#6B6E69` |
| radii | `--radius-selector/field .75rem`, `--radius-box 1rem` |
| borders/depth/noise | `1px` / `0` / `0` |

Fonts: system sans stack (Inter, DM Sans, ui-sans-serif…). No Google Fonts `@import`, no Anton. Display = same sans via unlayered `.font-display { font-weight:700; letter-spacing:-0.02em }` (beats utilities-layer `font-normal` on all existing `font-display` usages).

## What changed, per file

- `app/static/main.css` — wholesale rewrite. New tokens above; deleted Anton import, `halftone`/`halftone-drift`/`sparks`/`seal`/`seal-avatar` utilities + keyframes; added `.page-head`, `.kpi-strip`/`.kpi`, `.section-label`, `.avatar-ring`; restyled `.ledger-row` (canvas hover wash), `.dock` (pine active dot), `.today-rail .tab-active` (pine pill), `.app-header` (56px, paper/88 blur, 1px hairline), `.pulse-ember` (kept — `motion.js` adds it — ring now pine), shimmer/toast/modal keyframes recolored. Legacy class rebinds so untouched templates keep working: `ember→pine`, `lavender-whisper→#E8E6DF`, `vast-ink→ink` (only legacy names still used; all others deleted).
- `app/templates/pages/owner/dashboard.html` — heading block → `.page-head` (title + sub + timeframe select, hx attrs verbatim).
- `app/templates/components/dashboard_stats.html` — full rewrite: halftone hero → 4-up `.kpi-strip` (active/inactive/training/diet, count-up kept), plans card → hairline ledger with 3 rows.
- `app/templates/components/dashboard_content.html` — 2-col grid; seal count → soft badge; `text-ember` icons kept (token now pine).
- `app/templates/components/coach_stats.html` — seal chip → soft badge; footer pill → 16px radius.
- `app/templates/pages/owner/trainee/trainees.html` — header → `.page-head`; search collapse → sticky + sparks removed; `seal-avatar` → `.avatar-ring`; chevron → ghost btn; dashed empty box → centered message + CTA (existing msgids only).
- `app/templates/pages/user/dashboard.html` — halftone hero + warning alert → quiet `.page-head` (both existing msgids kept, warning msgid dropped per spec); Today rail → 16px hairline; Done buttons de-bordered ×3; fixed 2 mis-closed `{{ _('Other') }}` spans.
- `app/templates/pages/auth/login.html` — hero (halftone + sulfur badge + `-mt-14` overlap) deleted; centered card 400px, 1px border, 16px radius, small primary logo mark, hairline footer divider (sparks removed).
- `app/templates/layouts/dashboard.html` — dock Add trainee item removed (4-item max); rest via sweep.
- `app/templates/base.html` — iOS splash hexes → `#F1F0EB` / `#1A1E1C`.
- Global sweep over all `app/templates/**/*.html`: `border-2 family → border-1`, `border-base-content(/x) → border-base-300`, `divide-base-content → divide-base-300`, `rounded-[2.5rem]/[2rem] → 2xl`, `rounded-[1.5rem]/[1rem] → xl`, `class="seal" → class="section-label"`, `badge … rounded-full → badge` (default radius).
- `DESIGN.md` rewritten (Slate Pine contract), `PRODUCT.md` brand paragraph updated, `docs/redesign-caldera-evolved.md` marked superseded.

## Constraints honored

No hx-*/Alpine/form-name/_() mechanism changes, no routes/services/PocketBase touched, no new deps, no shadows/gradients/glass, `pulse-ember` + `data-count-up` JS contracts preserved.

## Verification

- `npm run build` ✓ (app.css 180.79 kB, app.js rebuilt)
- `python3 -m compileall app` ✓
- `grep -iE 'fc5000|524ae9|f5f28e|anton|halftone|fonts.googleapis'` over `app/**/*.css` + `app/templates` → **0 matches**
- `grep -iE 'border-2|border-t-2|rounded-\[|border-base-content|divide-base-content|\bseal\b|sparks|halftone'` over `app/templates` → **0 matches**
- `pytest -q` → **55 passed**
