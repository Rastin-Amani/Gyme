# Brag Plan: Gyme

## What is this app?
Gyme is a multi-tenant gym coaching platform: every gym gets its own branded, installable app. Owners and coaches publish training, diet, and steroid plans, and each trainee opens their phone in the morning to find today's plan waiting — the app greets them as **Champion**, and a single tap of **Done** closes the day.

## The angle
A quiet, premium launch for a very personal product. The camera never leaves the product's own design language: cream canvas, dark velvet chambers, 2px ink borders, EB Garamond serif. The video's premise is *the app already knows who you are* — it opens, calls the trainee by name, calls them a Champion, and hands them their day. The brag is not "we made a SaaS" — it's "every gym deserves to feel like this."

## Hook (first 2-3 seconds)
A phone rises out of the dark chamber and settles onto the cream desk. Its Today screen is already open: the greeting "**Champion**, welcome back 👋🏻" — with the name Champion set large in display serif. No setup, no logo first. The product moment IS the hook.

## Key moments (the middle)
- **Every gym gets its own app.** Three gym monogram tiles (A, B, M — lavender squares on cream, the app's own tenant-logo fallback) snap in one by one — three different gyms (Aspen, Birch, Maple), three different apps, one platform underneath.
- **The day's plan, done right.** Inside the app: tabs Nutrition 🥑 / Training 💪🏻 / Steroids 💊; the Training tab opens and three real exercise cards land one at a time — Squat, Bench Press, Deadlift — with the app's real badges: sets × reps, kg, seconds.
- **Done.** A finger taps the big lavender Done button; the ember pulse-ring fires (the app's own `pulse-ember`), the button flips to a check, the day advances.

## Outro / punchline
The dark chamber returns. The **Gyme** wordmark in cream Garamond, flanked by the app's two waveform decorations, and one line:
"Every gym, its own app. Every trainee, a champion."

## User flow worth showing
1. **Entry** — trainee opens the branded app; Today screen greets "Champion, welcome back 👋🏻" (real greeting structure: `{first_name}` + welcome-back).
2. **Key action** — plan list shows real training items with sets×reps / weight / rest badges; finger taps the big `Done` button.
3. **Result** — ember pulse-ring + check; day is done and the plan advances (the real `/user/plans/{plan_id}/done` → HX-Refresh behavior).

## Tone
- Preset: **polished**
- Creative direction: "cream broadsheet meets dark velvet chamber" — an elegant, calm launch; restraint is the luxury.
- Interpretation: 4 scenes, longer holds, slow crossfades and soft slides. Few words, generous serif type, real product UI on screen. Music low and steady; 2-3 tasteful SFX. Nothing flashy — the product's design language is the spectacle.

## Format: landscape — 1920x1080
## Duration: 19.5s

## Visual identity (from the project — Gyme theme ONLY)
- Background: `#1a1a1a` (vast ink, dark chamber) and `#ffffeb` (lumen cream) — scenes alternate between the two.
- Accent: `#f0d7ff` (lavender whisper, fill-only) with `#034f46` (forest ink) for text accents and `#ffa946` (ember glow) for the Done pulse.
- Text: `#1a1a1a` on cream; `#ffffeb` on dark. Muted `#5f5f56` (fog) for secondary UI.
- Phone body: `#e4e4d0` (lumen stone), 2px ink border, 52px radius — no gradient chrome, no shadows.
- 2px ink border is the signature; depth comes from borders/fills/radii, never shadows.
- Display font: EB Garamond (400/500/600). Body font: Figtree.
- Strongest visual element: the trainee Today card — cream, 2px ink border, 32px radius, lavender Done button, ember ring.

## Share copy (draft)
```
Gyme gives every gym its own app. Open it in the morning and it greets you by name — "welcome back, champion" — then your whole day is one tap away.
Every gym, its own app. Every trainee, a champion. 💪🏻
```

## Audio direction
- Role: warm bed — sparse, professional accents; music carries the calm energy.
- Music: `happy-beats-business-moves-vol-12-by-ende-dot-app.mp3` (1:58, ~110 BPM, steady and clean — the `polished` pick).
- Music treatment: fade in over 0.6s at the hook, sit ~0.32 volume, dip subtly during the Done moment, let the final logo SFX ring over a gentle fade-out at the end.
- Music cue guidance: bundled preset at `<skill-dir>/assets/music/cues/happy-beats-business-moves-vol-12-by-ende-dot-app.music-cues.{md,json}` — tempo ~110 BPM; strong cues at 8.74s, 13.11s, 17.47s in the 0-25s planning window; beat grid from 0.56s at ~0.55s spacing. Major locks: scene 3 phone settle to the 8.74s strong cue; the Done pulse to 13.11s; outro lockup to 17.47s. Sequential items (3 monograms at 5.34/6.00/6.56, 3 exercise cards at 9.83/10.37/10.93) snap to consecutive beats, but each readable line holds for its reading-time floor — text outranks the grid.
- Audio-reactive treatment: subtle; let RMS breathe the lavender glow behind the phone and the cream "desk" vignette. No waveform/equalizer visuals.
- SFX posture: sparse and polished — phone settle, three soft monogram ticks, three quiet card landings, one tap + soft success chime for Done, one low bell for the logo.
- Audio-coupled moments: phone settle at hook; monogram arrives (one per beat); exercise card sequence (one per card); the Done tap; the final logo bell over the fade.
- Restraint rule: no loud or dense SFX; no multiple hits per second; music never above 0.4; nothing that fights the calm.

## Storyboard

### Scene 1 — Hook: "Welcome back, Champion" — 3.5s
Dark chamber (`#1a1a1a`) fills the frame. A cream phone card (2px ink border, 52px radius, `#e4e4d0` body) slides up from below with a soft settle onto an implied cream desk. On screen, the real Today greeting on a cream card: `Champion` in EB Garamond forest ink + `welcome back` 👋🏻 — the hook line — set large in display serif beneath the small app header (Aspen Gym). Pill badge: "Your plan for today is ready". Dock: Profile / Today (active) / Plans.
Sequential/interaction: yes — phone rises, greeting assembles (name first, then greeting, then the pill lands last).
Audio intent: warm, anticipatory; the settle is the first beat.
Audio-coupled idea: phone settle SFX; Champion line lands with a soft drop.
Music: steady loop, low volume, fade-in from 0.
Transition mood: soft crossfade (0.6s) → Scene 2.

### Scene 2 — Reveal: "Every gym gets its own app" — 4.5s
Cream canvas. Big EB Garamond headline: **Every gym gets its own app.** — support line beneath: Your gym. Your name. Your app. Three lavender monogram tiles (A, B, M — 2px ink borders, 32px radius, ink letters, the app's tenant-logo fallback) slide in one by one from the right, each with its own small caption line under it (a gym name: Aspen / Birch / Maple) and an "own app" pill. Each monogram is the seed of its own branded app.
Sequential/interaction: yes — three tiles, one per beat, each arriving with a soft tick.
Audio intent: bright and calm; each tile is a quiet "another gym, another app".
Audio-coupled idea: monogram by monogram, aligned to consecutive beats (5.34/6.00/6.56).
Music: full bed at ~0.32.
Transition mood: clean wipe (0.45s) → Scene 3.

### Scene 3 — Highlight: The plan, one tap, day done — 8s
Dark chamber again. Phone card settles center. Inside: tabs Nutrition 🥑 / Training 💪🏻 (active) / Steroids 💊. Three training cards land one at a time on a beat grid — Squat (4 sets × 12 reps), Bench Press (4 sets × 10 reps · 70 kg · 90 sec), Deadlift (4 sets × 8 reps · 90 kg · 120 sec) — with small category dividers (Warm-up → Main). A finger taps the big lavender **Done** button; an ember ring fires (pulse-ember), the button flips to a checked done state, and the day advances. Small cream caption under the phone: "One tap. Day done."
Sequential/interaction: yes — 3 cards one by one; simulated finger tap on the Done button.
Audio intent: rising warmth through the cards; the tap is the payoff; soft success chime on the ring.
Audio-coupled idea: card landings on beats (9.83/10.37/10.93); tap SFX + success chime; ring-out aligned to the 13.11s strong cue.
Music: steady; duck ~0.05 for the tap→chime beat.
Transition mood: soft crossfade (0.6s) → Scene 4.

### Scene 4 — Outro: Lockup — 3.5s
Dark chamber. The cream **Gyme** wordmark (Garamond), flanked by the two waveform decorations from the login footer. Tagline: **Every gym, its own app. Every trainee, a champion.** / Training · Nutrition · Daily plans. Gentle settle; fade to near-black.
Sequential/interaction: none — one composed lockup.
Audio intent: calm resolution; the final bell rings over the fade.
Audio-coupled idea: logo settle toward the 17.47s strong cue; low bell on the settle; music fades under it.
Music: fades out over the last 1.2s.
Transition mood: end on fade-to-black, hold, fade-out.

**Total: 3.5 + 4.5 + 8 + 3.5 = 19.5s**

**Music mood for this video:** polished, steady, warm business loop.
**Audio summary:** A calm 110 BPM bed carries the whole video; three quiet monogram ticks, three card landings, one tap + success chime, and a low logo bell — every SFX earned, nothing loud.