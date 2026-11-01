# Mascot plan (exploration only)

No design has been chosen. Outputs: `L:\naqsh-review\mascot\` (concepts, expressions,
contact-sheet.jpg 2220×2060). Prompts/manifest: `docs/mascot-manifest.json`,
`backend/scripts/build_mascot_*.py`. Costs in ASSETS.md.

## Chosen design → one hand-authored SVG

When the owner picks one, rebuild it as a **single hand-authored SVG under 30 KB**, not a
traced/raster image:

- One `<svg viewBox="0 0 64 64">`, 3–5 paths for the body/ink/sheets, two dot eyes, one
  mouth, optional dots. Flat fills from `#5B6CFF` family + cool neutral; no gradients.
- Transparent background by construction; a 32 px test at 1× and 2× DPR.
- Expressions as **separate groups** (`#idle`, `#thinking`, `#happy`, `#sad`, `#wave`) toggled
  by a class on the root; no per-frame image swapping.

## CSS states

| State | Visual | Trigger |
|---|---|---|
| idle | blink every 4 s, tiny breathing | default |
| thinking | three dots step in/out, slight tilt | loading |
| wave | one raised nub/edge rotates ±12° twice | hover/focus |
| happy | eyes closed, small bounce | export success |
| sad | eyes down, 4° tilt, dim | error |

Animation uses `animation-timing-function: steps(1, end)` at **12 fps** (retro low-fps),
e.g. a 6-frame blink at 83 ms steps. `@media (prefers-reduced-motion: reduce)` disables all
keyframes and shows the static state.

## Integration

`StateIllustration` is the single slot: map `loading → thinking`, `empty → idle`,
`success → happy`, `error → sad`. The mascot replaces the placeholder icon inside the
existing single icon slot; no per-screen icons. Hover/focus wave is CSS only.

## Video use

- Render the SVG at 1024×1024 with a transparent background (Playwright `omitBackground`)
  for each state; Recordly overlays the PNG/SVG on the UI.
- If motion is needed, export a 12 fps PNG sequence from the same SVG (5 states + loops),
  with the same steps timing; no AI frames in the video.
- Keep the mascot out of frames where it would imply an assistant/chat; it only reacts.

## Fallback if frame consistency fails

The raster expression tests already show **layers** shifting silhouette between states.
Fallback: author all states by hand in the single SVG (paths shared, only face/pose groups
changed), so identity is exact; do not interpolate or swap AI frames. If 32 px legibility
still fails, drop to a dot-only mark or no mascot in the UI (keep it decorative only).

## Estimate (labeled estimate)

| Work | Hours |
|---|---|
| Hand-author SVG + 5 states | 6–10 |
| CSS states, 12 fps steps, reduced motion | 3–5 |
| StateIllustration integration + tests | 2–3 |
| Video transparent renders / sequence | 1–2 |
| **Total** | **12–20 h** |

## Risks

- `dot-b` and `nib` have an extra pale blob above the character; `knot` reads like an
  ampersand, close to a letterform. None is a final pick.
- 32 px legibility has not been tested; the SVG must be checked at that size.
- Character consistency across AI frames is not reliable (see `docs/mascot-expressions.md`).
