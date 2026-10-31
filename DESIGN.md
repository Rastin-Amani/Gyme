# Design — Gyme Slate Pine (DaisyUI only)

Calm premium gym SaaS. Paper canvas, deep pine actions, warm ink. This supersedes
the Caldera direction and the intermediate custom-class pass: the interface is now
built **exclusively from one DaisyUI theme plus Tailwind utilities**. There are no
custom component classes in `app/static/main.css` — if the product needs a new look,
the theme tokens change, not the markup contract.

## Tokens (`@plugin "daisyui/theme"` in `app/static/main.css`)

- paper `#FBFBF9` (base-100) · canvas `#F2F1EC` (base-200) · hairline `#E4E2DA` (base-300) · ink `#191D1B` (base-content)
- pine `#1C4A3C` = the only actionable colour (primary: CTAs, active nav, Done, focus, selection)
- stone `#57534E` (secondary) · moss `#A3B18A` (accent — status only, never surfaces)
- semantic: info `#0E7490` · success `#15803D` · warning `#B45309` · error `#B91C1C`
- radius: 10px selector + field · 16px box. Borders 1px. `--depth: 0`, `--noise: 0` → flat by contract.
- control height: `--size-field: .28125rem` → 45px buttons/inputs/tabs (thumb-sized without per-element utilities).
- type: the platform system stack (Tailwind default). No webfont is fetched: SF Pro on Apple
  platforms, Segoe/Roboto elsewhere. Hierarchy comes from weight + size + tracking
  (`tracking-tight` on titles, near-zero on body), never from colour alone.

## Direction contract

- THESIS: a quiet ledger, not a loud dashboard. One paper surface on a canvas, pine stamps where
  action lives, hairlines where structure lives, translucency only where chrome floats over content.
- OWN-WORLD: persistent shell (translucent sticky header, sidebar `menu` on desktop, `dock` on mobile),
  page title + sub, `stats` strip, `list`/`list-row` ledgers, `tabs-box` segmented rails, DaisyUI modals.
- STORY: coach scans the stats, drills into a ledger row, acts. Trainee opens Today, reads the plan
  sections, presses the pine Done.
- FINISH: unreviewed and undocumented is unfinished — this build ends with the verification below.

## Rules

- **No custom classes.** Build from DaisyUI components (`card`, `list`, `stats`, `menu`, `dock`,
  `tabs`, `collapse`, `fieldset`/`input`/`select`/`textarea`, `modal`, `alert`, `badge`, `btn`,
  `avatar`, `indicator`, `status`, `radial-progress`, `divider`, `loading`, `skeleton`) and Tailwind
  utilities. `main.css` holds the theme block and Alpine's `[x-cloak]` only.
- Flat: no shadows, no gradients, no glass decoration, no coloured border-left, no zoom hovers.
  Press compresses (`active:scale-[0.98]` on primary CTAs), hover is a tone change or 1px border shift.
- Translucency is structural: the sticky header (`bg-base-100/80 backdrop-blur-xl`) and the mobile
  dock are the only blurred surfaces. Never stack glass on glass.
- Icons are drawn SVG (1.6–1.8 stroke, `currentColor`), one system, and they come from one
  registry: `icon("name", "classes")` in `app/templates.py`, never inline `<svg>` in a template.
  Page chrome is the same idea — `page_header`, `detail_header` and `section_title` from
  `components/ui.html`, so titles, badges, actions and section labels land in the same place on
  every page. Emoji are not iconography; languages are listed by native name behind one language
  icon (flags render as letter pairs or tofu on Windows).
- No kicker/eyebrow above titles. Section labels are small caps from `section_title`, with no rule
  above them.
- Motion: CSS/DaisyUI transitions + existing `motion/mini` settle, stagger and count-up. Nothing
  gesture-driven is hand-animated; all of it collapses under `prefers-reduced-motion`.
- States everywhere: hover, active, focus-visible (2px pine outline), disabled, loading (DaisyUI
  `loading`), empty (dashed `card` with a calm line and one CTA), error (`validator` + `alert`),
  offline banner kept.
- Numbers use `tabular-nums`; counts animate once via `data-count-up`.

## Component mapping

| Surface | Component |
| --- | --- |
| App shell | `max-w-[82rem]` flex; `sticky h-dvh` sidebar; `navbar sticky top-0 bg-base-100/80 backdrop-blur-xl`; mobile `dock` |
| Navigation | `menu menu-md` + `menu-active`; `dock` + `dock-active` + `dock-label` |
| Page head | `text-2xl/3xl font-semibold tracking-tight` + `text-sm text-base-content/60` sub, action right |
| KPIs | `stats stats-vertical sm:stats-horizontal` with `stat-title` / `stat-value` / `stat-desc` |
| Ledgers | `list` + `list-row` (hairline dividers, 1fr growth, `hover:bg-base-200/60`) |
| Segmented control | `tabs tabs-box bg-base-200 p-1` + `tab tab-active` |
| Forms | `label.input` / `label.select` with `<span class="label">`; textareas via `floating-label`; `validator` |
| Detail rows | `list` with `label → value (ms-auto)` pairs — no centred KPI grids |
| Modals | `dialog.modal.modal-bottom sm:modal-middle` + `modal-box` + `modal-action`; photo lightbox uses native `<dialog>` |
| Toasts | `toast toast-center sm:toast-end` container + `alert alert-{tone} alert-soft` |
| Empty | `card border-dashed` + `card-body items-center text-center py-12` |

## Quality bar

- Contrast ≥4.5:1 body, ≥3:1 large; 45px controls; 65–75ch measure; no horizontal overflow at 390px.
- Desktop 1440 and mobile 390 both calm; the dock, header and modal/toast roots survive HTMX swaps
  (only `#page-content` is replaced).
- No webfont request; CSS ships as one file with the theme inlined; no second component library and
  no new runtime dependency.
