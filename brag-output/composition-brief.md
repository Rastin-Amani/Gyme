# Hyperframes Composition Brief: Gyme

## Objective
Create a short launch-style brag video for **Gyme**, a multi-tenant gym coaching platform where every gym gets its own branded installable PWA and every trainee is greeted by name each morning on their "Today" dashboard.

## Output
- Composition directory: `brag-output/composition/`
- Rendered video: `brag-output/brag.mp4`
- Format: landscape — 1920x1080
- Duration: 19.5s

## Source Material
- Project root: `/workspace/projects/Gyme`
- Primary files read: `app/static/main.css` (design tokens), `app/templates/base.html`, `app/templates/layouts/dashboard.html`, `app/templates/pages/auth/login.html`, `app/templates/pages/user/dashboard.html` (Today screen), `app/templates/pages/owner/dashboard.html`, `app/templates/components/dashboard_stats.html`, `app/routes/user/dashboard.py`, README, package.json
- Product name: **Gyme**
- Tagline / strongest claim: "Every gym gets its own app. Every trainee, a champion."
- Key UI or visual moment to recreate: the trainee **Today** screen — cream card, 2px ink border, 32px radius, greeting "Champion, welcome back 👋🏻", big lavender **Done** button that fires an ember pulse-ring on completion (the app's real `pulse-ember`).
- Copy that appears (real UI strings from the project — English locale):
  - `welcome back` — greeting pattern `{first_name} welcome back`
  - `Done`
  - `Nutrition` 🥑 / `Training` 💪🏻 / `Steroids` 💊 (plan tabs)
  - Badges: `sets`, `reps`, `kg`, `sec`
  - Category dividers: `Warm-up` / `Main`
  - Wordmark: `Gyme`
  - Fictional stand-ins only: trainee name `Champion`; gym monograms `A / B / M`; gym names Aspen / Birch / Maple.
- **Language rule: English only.** No Persian copy anywhere in the video. The app's default locale is English; the video shows English UI.

## Creative Direction
- Tone preset: **polished**
- Creative direction: "cream broadsheet meets dark velvet chamber" — a quiet, elegant launch; restraint is the luxury.
- Interpretation: 4 scenes, longer holds, slow crossfades (0.6s) and soft slides. Few words, generous EB Garamond serif type, real product UI on screen. Music low and steady; 2-3 tasteful SFX. The product's own design language is the spectacle.
- Angle: The app already knows who you are — it opens, calls the trainee a Champion, and hands them their day. One tap closes it.
- Hook: A phone rises out of the dark chamber onto the cream desk; the Today screen is already open with "Champion, welcome back".
- Outro / punchline: Gyme wordmark in cream Garamond flanked by the login footer's two waveform decorations; "Every gym, its own app. Every trainee, a champion."
- Avoid:
  - Generic SaaS language ("streamline", "workflow")
  - Abstract filler visuals / color washes
  - Unrelated visual redesign — stay inside the project's palette and type
  - Any non-Gyme color — no graphite, no white contact circles, no gray gradients

## Visual Identity (Gyme theme — ONLY these tokens)
- Background: alternates `#1a1a1a` (vast ink — dark chamber) and `#ffffeb` (lumen cream) / `#e4e4d0` (lumen stone)
- Text: `#1a1a1a` on cream; `#ffffeb` on dark; muted `#5f5f56` (fog) for support text
- Accent: `#f0d7ff` (lavender whisper — fills only, never text on cream), `#034f46` (forest ink — text accents on cream), `#ffa946` (ember glow — Done pulse on dark)
- 2px ink border is the signature; depth from borders/fills/radii only — **no box-shadows, no graphite gradients, no white**
- Display font: EB Garamond (Latin)
- Body font: Figtree
- Visual references from the project: Today dashboard card, tenant-logo lavender monogram fallback (rounded square, 2px border), waveform decoration (5 staggered bars), badge pills (9999px radius), dash divider lines, 2px ink border + 32px radius + 12px control radius, `.btn` active scale 0.97, `pulse-ember` ring-out (2px accent border, opacity 0.85→0, scale 1→1.16, 0.55s)

## Storyboard
Use the storyboard in `brag-output/brag-plan.md` as the creative contract.

Scene summary:
1. Hook: "Welcome back, Champion" — 3.5s — dark chamber; phone settles; Today greeting `Champion` + `welcome back` 👋🏻 in display serif
2. Reveal: "Every gym gets its own app." — 4.5s — cream canvas; EB Garamond headline; 3 lavender monogram tiles A/B/M (Aspen/Birch/Maple) arrive one by one
3. Highlight: The plan, one tap, day done — 8s — phone Today screen; tabs; 3 training cards (Squat / Bench Press / Deadlift) with real badges; finger taps `Done`; ember ring fires; button flips to checked
4. Outro: Lockup — 3.5s — dark chamber; Gyme wordmark + waveform decorations; tagline

## Audio
- Audio role: warm bed — sparse, professional accents; music carries the calm energy
- Audio arc: fade-in at the hook → steady through careful lifts → small duck for the tap → logo bell over gentle fade-out
- Music: `happy-beats-business-moves-vol-12-by-ende-dot-app.mp3` → copied to `assets/music/`
- Music treatment: fade in over ~0.6s at 0s, sit ~0.32 volume, duck ~0.05 for the Done tap→chime beat, fade out over the last ~1.2s
- Music cue guidance: bundled preset `<skill-dir>/assets/music/cues/happy-beats-business-moves-vol-12-by-ende-dot-app.music-cues.{md,json}` — tempo ~110 BPM; strong cues at 8.74s, 13.11s, 17.47s (0-25s window); beat grid from 0.56s at ~0.55s spacing. Scene 3 phone settle locks to 8.74s; Done pulse to 13.11s; outro lockup to 17.47s. Monograms at 5.34/6.00/6.56 and cards at 9.83/10.37/10.93 snap to beats; text readability outranks the grid
- Audio-reactive treatment: subtle — RMS/bass breathes the lavender glow behind the phone and the cream vignette; no waveform/equalizer visuals
- Audio-coupled moments:
  - Hook — phone settle SFX; Champion line lands with a soft drop
  - Reveal — 3 monogram tiles, one per beat, soft ticks
  - Highlight — 3 card landings on beats; tap SFX + success chime on the ring-out
  - Outro — logo settle toward a strong cue; low bell over the fade
- SFX selection guidance: polished and sparse — phone settle, soft ticks/drops, one tap, one quiet success chime, one low bell. Use `<skill-dir>/assets/sfx/sfx-analysis.md` (+.json) for selection; prefer low high-frequency-risk files for repeated moments. Exact filenames, timestamps, density, and volume chosen after the animation exists, per the implemented motion.
- Exact SFX choice: delegated to composition authoring (chosen after the visuals are implemented), copied into `assets/sfx/`
- Audio files: copy `happy-beats-business-moves-vol-12-by-ende-dot-app.mp3` into `brag-output/composition/assets/music/`; copy EB Garamond + Figtree WOFF2 into `assets/fonts/`

## Hyperframes Instructions
Load the composition-building Hyperframes domain skills — `hyperframes-core` (composition contract + `data-*` timing), `hyperframes-animation` (motion), `hyperframes-creative` (design spec, beats, audio-reactive), `hyperframes-keyframes` (seek-safe keyframes), and `hyperframes-cli` (lint/check/render). /brag is its own workflow: do not enter the `hyperframes` entry-point intent interview and do not route into its generic promo / launch-video workflow. Prefer native Hyperframes conventions.

Requirements:
- Show at least one real UI element from the source project (the Today dashboard card with the English locale copy).
- Keep all text readable in the final render — respect the reading-time floor (~0.8s settled for short labels, ~0.3s/word for sentences).
- Keep the video within 15-25 seconds (target 19.5s).
- Include the planned music/SFX layer.
- Treat music cue metadata as optional timing hints; ignore cues that hurt readability, pacing, or the product story. Major reveals may move toward nearby strong cues within ±0.15s; smaller entrances within ±0.10s of beats. Use 1-3 strong cue locks.
- Use SFX to support motion and interaction, with polished restraint.
- Consider the audio-reactive workflow (subtle only) once music is placed.
- Use local assets for audio and fonts.
- Run `npx hyperframes check` before render — brag's single gate.