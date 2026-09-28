# Design — Gyme Slate Pine

Calm premium gym SaaS. Paper canvas, deep pine actions, warm stone text. Replaces Caldera Evolved (ember/violet/sulfur eye-burner) — rationale and change list in `docs/retheme-slate-pine.md`.

## Tokens

- paper `#FAFAF8` (base-100) · canvas `#F1F0EB` (base-200) · hairline `#E4E2DA` (base-300) · ink `#1A1E1C` (base-content)
- pine `#1C4A3C` = the only actionable color (primary: CTAs, active tab, Done, focus ring, dock dot, selection)
- stone `#57534E` (secondary) · moss `#A3B18A` (accent — sparingly: tiny badges/status only, never surfaces)
- fog `#6B6E69` = meta text (AA on paper)
- semantic: info `#0E7490` · success `#15803D` · warning `#B45309` · error `#B91C1C`
- Type: system sans stack (Inter/DM Sans first if installed, no webfont fetch). Display = same sans 700/800, tracking −0.02em (`.font-display`).
- Radius: 12px fields/selectors · 16px boxes. Borders: 1px hairlines. Depth: 0, noise: 0.

## Direction contract

- THESIS: a quiet ledger, not a loud dashboard. One column of soft paper on canvas, pine stamps where action lives, hairlines where structure lives.
- OWN-WORLD: compact sticky blurred header, page-head title + sub, KPI strip with tabular counts, hairline ledger rows with hover wash, segmented Today rail with pine active pill, safe-area dock with pine active dot, roster avatars with status dot.
- STORY: coach scans the KPI strip, drills into a ledger row, acts. Trainee opens Today, reads the plan sections, taps the pine Done.
- FINISH: unreviewed and undocumented is unfinished — this build ends with the docs and verification below.

## Rules

- Icons are drawn SVG (1.5–2 stroke, currentColor), one system. No emoji as iconography (flags in locale switcher stay).
- No kicker/eyebrow above headings. Headings carry their own weight; `.section-label` labels sections, not titles.
- No gradient text, no glass decoration, no colored border-left, no drop shadows, no zoom/scale-up hovers. Press compresses (0.97), hover lifts (−2px translate) — never zooms.
- No 800px pills: pills only for avatar, status dot, toggle. Surfaces are 16px, fields 12px, badges DaisyUI default (selector radius).
- Motion vocabulary (CSS + existing motion/mini only, no new deps): page settle fade-rise, stagger, count-up numerals, tab pill slide, Done morph + pine ring-out, toast slide-in, modal pop, skeleton shimmer on htmx-request. All collapse under prefers-reduced-motion.
- Browser surfaces themed: selection pine, focus-visible 2px pine outline (offset 2), scrollbar thin stone, caret pine, tabular numerals for counts.
- States everywhere: hover, active, disabled, loading (DaisyUI loading spinner + shimmer), empty (calm centered message + CTA), error (validator-hint + alert), offline banner kept.

## Components

- `.page-head`: title (1.5rem/700/−0.02em) + `.page-sub` fog sub, action right-aligned.
- `.kpi-strip` / `.kpi`: 2-col → 4-col, 1px hairline, 16px radius, uppercase label, 28px/800 tabular value, fog note.
- `.section-label`: 11px/700 uppercase tracking .08em fog (replaces Caldera seals).
- `.ledger-row`: hairline dividers, hover bg canvas, `.ledger-go` chevron slides +4px and turns pine.
- `.avatar-ring`: pine-wash circle, 1px ring, status dot (success/fog) with paper outline.
- Header: sticky top, paper/88 blur, 1px ink/12% bottom hairline, min-height 56px.
- Dock: fixed bottom, safe-area padding, 4 items max (owner/coach) / 3 (trainee), active = ink 700 + pine dot.
- Buttons: btn-primary pine, arrow nudges +3px on hover; loading state keeps width.
- Tabs (Today): segmented rail (canvas, 1px hairline, 16px) with pine active pill via Alpine `:class` only — no JS change.
- Forms: 12px fields, pine focus ring, validator-hint errors.
- Toasts: paper chamber, 1px hairline, 16px radius, DaisyUI alert tones, slide-in + auto-dismiss.
- Modal: pop-in (fade + 8px rise), paper 16px chamber.

## Quality bar

Contrast ≥4.5:1 body, ≥3:1 large; 44px touch targets; 65–75ch measure; desktop 1440 + mobile 390 both calm, no horizontal overflow; HTMX swaps settle without flash; Alpine store untouched.
