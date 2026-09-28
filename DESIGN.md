# Design — Gyme Caldera Evolved

Caldera kept, execution fixed. Same tokens, same triple-radius, same shadowless forge. What changes is hierarchy, rhythm, and motion.

## Tokens (unchanged)

- pumice `#e2e2df` canvas · limestone `#f7f6f2` surface · obsidian `#070607` ink · chalk `#fff`
- ember `#fc5000` = the only actionable color (CTAs, active tab pill, Done, focus ring, dock dot)
- plasma violet `#524ae9` = hero halftone ground only, never controls
- sulfur `#f5f28e` = section tags only
- fog `#6a6964` = meta text (AA on limestone)
- Anton display (headings, numerals) · DM Sans UI body
- radius: 800px pills · 100px fields · 40px surfaces · 2px obsidian borders · depth 0

## Direction contract

- THESIS: a forge ledger, not a SaaS dashboard. One column of limestone paper on pumice, ember stamps where action lives, sulfur tags where structure lives. Refuses the hero-metric card grid and the emoji-led headings.
- OWN-WORLD: halftone hero chambers, sulfur section seals, ember pill CTAs with arrow-nudge, hairline ledger rows with status dots, segmented tab rail with sliding ember pill, sticky blurred header, safe-area dock with ember active dot.
- STORY: coach scans gym pulse (counts animate up), drills into a ledger row, acts. Trainee opens Today, reads the meal/block seal, taps the big ember Done.
- FIRST VIEWPORT: sticky header (back + title + gym seal) → display heading with sulfur count seal → ember/timeframe control row → halftone pulse chamber with count-up numerals → ledger sections sealed by sulfur tags.
- FORM: evolved Caldera, second on the seven-candidate list (first was full replacement world, rejected — brand equity in ember/limestone too high).
- FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance.

## Rules

- Icons are drawn SVG (1.5–1.8 stroke, currentColor), one system. No emoji as iconography (flags in locale switcher stay — they are language names, not icons).
- No kicker/eyebrow above headings. Headings carry their own weight; sulfur seals label sections, not titles.
- No gradient text, no glass decoration, no colored border-left, no hard offset shadows, no zoom/scale-up hovers. Press compresses (0.97), hover lifts (−2px translate) — never zooms.
- Motion vocabulary (CSS + existing motion/mini only, no new deps): page settle fade-rise 220ms, stagger 8–14 rows, count-up numerals, tab pill slide, Done morph to success check, toast slide-in, modal pop, dock lift, skeleton shimmer on htmx-request, spark flicker heartbeat. All collapse under prefers-reduced-motion.
- Browser surfaces themed: selection ember, focus-visible ember ring, scrollbar limestone/obsidian, caret ember, tabular numerals for counts.
- States everywhere: hover, active, disabled, loading (DaisyUI loading spinner + shimmer), empty (dashed limestone chamber), error (validator-hint + alert), offline banner kept.

## Components

- Header: sticky top, limestone/85 blur, hairline bottom border, back button ghost-circle, title semibold, gym seal avatar 10×10 rounded-xl 2px obsidian.
- Dock: fixed bottom, limestone, top 2px border, safe-area padding, 5 (owner) / 3 (trainee) items, active = obsidian text + ember dot above label, inactive = fog.
- Buttons: btn-primary ember pill, arrow icon nudges +4px on hover; btn-ghost for secondary; loading state keeps width (no layout shift).
- Tabs (Today): segmented rail (limestone, 2px obsidian, 40px) with ember active pill sliding via Alpine :class only — no JS change.
- Ledger rows (trainees/plans/items): 2px obsidian chamber, divide hairlines, avatar ember-wash seal with status dot, chevron slides +4px on hover.
- Stat chamber: halftone hero with chalk Anton numerals (count-up), limestone ledger below; coach rows with tabular numerals.
- Forms: floating-label inputs, ember focus ring, validator-hint errors, sticky bottom CTA on mobile.
- Toasts: limestone chamber, 2px obsidian, left ember/info/success/error spine via DaisyUI alert tones, slide-in + auto-dismiss, click to dismiss.
- Modal: pop-in (fade + 6px rise), limestone 40px chamber, backdrop obsidian/40.

## Quality bar

Contrast ≥4.5:1 body, ≥3:1 large; 44px touch targets; 65–75ch measure; display ≤6rem; tracking ≥−0.04em; desktop 1440 + mobile 390 both calm, no horizontal overflow; HTMX swaps settle without flash; Alpine store untouched.
