# Demo script — 3:00, English

Only features that exist and are tested appear here. Every number traces to a receipt in
`fixtures/demo/*/receipt.json`. **No time-saved ratio is claimed** — the manual baseline is
still PENDING (`docs/time-saved.md`), so the video must not state one.

## Numbers used (from the demo receipts)

| Page | Regions | Recorded total | Recorded cost | Receipt |
|---|---|---|---|---|
| comic `01-comic-flat` | 3 | **39.8 s** | **$0.0280** | `fixtures/demo/comic/receipt.json` |
| menu `03-menu-paper` | 16 | **90.3 s** | **$0.0391** | `fixtures/demo/menu/receipt.json` |
| label `05-label-kraft` (honest limit) | 3 | **39.7 s** | **$0.0269** | `fixtures/demo/label-fail/receipt.json` |

These are replay receipts of real runs; the demo badge says so. Do not read them as live
waiting time.

## Shot list and narration

### 0:00–0:20 — Hook

**Shot:** home page (`/?clean=1`), slow push on the headline “Turn any page into editable
Arabic layers”. Cursor over the drop zone.

**Narration:** “Arabic comics and menus are still localized by hand: erase the lettering,
redraw the background, retype every line in Arabic, hope nothing moves. Naqsh turns one
page into editable Arabic layers — and gives every region back to you.”

### 0:20–0:45 — Upload the comic (demo replay)

**Shot:** upload `01-comic-flat.png`. Badge appears: **Demo mode — replaying a recorded
run**. Result shows before/after. Open the editor.

**Narration:** “This is a recorded run: three lettering regions, 39.8 seconds, 2.8 cents.
The badge stays on screen — the demo never pretends a replay is a live call.”

### 0:45–1:15 — Layers are real

**Shot:** Layers panel: **Scenery**, **2 bubbles**, **3 text**. Hide one bubble — the hole
in the scenery is visible; show it again. Rename the title. Drag a text layer above
another. Lock a layer and try to drag it.

**Narration:** “The background is not one image. Scenery, speech bubbles and text are
separate layers. Hide a bubble, rename a layer, reorder, lock it. Nothing here is baked
into a flat PNG.”

### 1:15–1:45 — Fix a line, draw a cover

**Shot:** select a text region, change one Arabic line, switch Arabic style, reset to the
AI result. Draw an ellipse cover patch with the colour control; undo.

**Narration:** “The editor is the product: fix a translation, change the register, or cover
artwork the model should not touch — every change is a layer edit, not a repaint.”

### 1:45–2:10 — Menu page

**Shot:** upload `03-menu-paper.png` (demo). Show 16 regions and **Scenery + text only** —
no invented bubbles. Point at prices keeping their numerals.

**Narration:** “A dense menu: sixteen regions, 90.3 seconds, 3.9 cents. No bubbles on this
page, so it gets scenery and text only — the rule is scene-aware, not one-size.”

### 2:10–2:30 — Export

**Shot:** Export menu: Layered SVG, Outlined SVG, PNG, Bundle (ZIP). Run PNG; show the
size toast. Open the ZIP: `layers.json`, `layers/scene.png`, `layers/bubble-*.png`, SVGs.

**Narration:** “Export is layered: SVG groups and a ZIP with a layers manifest and the
scene/bubble assets, so the page can go back into a design tool — not a flattened image.”

### 2:30–2:50 — Honest limit

**Shot:** upload `05-label-kraft.png`. The plate is not clean on the photographed label.

**Narration:** “This is where it still fails: a photographed label. The plate smears. I
show it because the editor is how you take over — and because a localizer that hides its
failures is not useful.”

### 2:50–3:00 — Close

**Shot:** repo, test count, demo badge.

**Narration:** “Naqsh: Arabic-first layers, scenery, bubbles and text, editable and
exportable. Built with Meta Muse Spark, SAM 3.1 and Muse Image.”

## What the narration must NOT say

- No time-saved ratio or “N× faster” — baseline PENDING.
- No “fully automatic”, “no editing needed”, “any language”.
- No “live model call” while the demo badge is on.
- No clean-plate success claim for the label page.
- No claim that the before/after divider is pixel-verified in the demo cache; it predates
  the frame-offset fix.

## Marked unverified (do not put on screen)

- Manual baseline and time-saved results — BLOCKED ON OWNER (#9).
- Live public URL requirement — PENDING (CV said a hosted URL is better).
- Outside AI coding tools — PENDING.
- The clean-plate gate (#3) — BLOCKED ON OWNER.
