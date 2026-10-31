# Demo script — live-first, 3:00, English

All main takes are **live** (`LIVE_MODE=1`), with the LIVE banner, stage progress and the
receipt visible. Demo replay appears only as a labelled fallback. Every number cites a
receipt; no time-saved ratio (owner decision 2026-10-29; “faster” only).

## Numbers

| Source | Number |
|---|---|
| Fresh-clone live comic, 2026-10-31 (`docs/evidence/fresh-clone-2026-10-31.md`) | **61.7 s**, **$0.039521** |
| Live comic receipt (`docs/evidence/test-suite/summary.json`) | **93.0 s**, $0.0436 (3 bubbles) |
| Demo receipt comic (`fixtures/demo/comic/receipt.json`) | 39.8 s, $0.0280 |
| Demo receipt menu (`fixtures/demo/menu/receipt.json`) | 90.3 s, $0.0391 |
| Demo candidates (`docs/evidence/demo-candidates.json`) | 45.2–93.6 s, $0.0251–$0.0459 |

Waits are recorded in real time; cuts carry a **“sped up”** or **“cut”** label and a timer.

## Shot list / narration

### 0:00–0:15 — Hook (live result already on screen)
**Shot:** the live comic result from take 1, LIVE banner visible.
**Narration:** “Arabic localization is still hand work. Naqsh turns one page into editable
Arabic layers — and this is a live run, not a recording.”

### 0:15–0:50 — Live upload (real wait, cut with label)
**Shot:** terminal banner `LIVE MODE`; upload the comic; stages tick.
**Narration:** “Live model calls: Muse Spark reads and translates, SAM segments, Muse Image
repaints. This take took 61.7 seconds and cost 3.9 cents; the receipt is on screen.”

### 0:50–1:25 — Layers are real
**Shot:** Layers panel: Scenery, bubbles, text; hide/show, rename, lock/drag; slider.
**Narration:** “Scenery, speech bubbles and text are separate layers — hide a bubble,
rename, reorder, lock it. Nothing is baked into a flat PNG.”

### 1:25–1:55 — Edit and export
**Shot:** change one line, switch Arabic style, draw a cover, open Export, download ZIP,
show `layers.json` and `layers/`.
**Narration:** “Every fix is a layer edit. Export gives real SVG groups and a ZIP with the
layer manifest and scene/bubble assets — not a flattened image.”

### 1:55–2:25 — Live menu (second page type)
**Shot:** live menu upload; show prices/digits and the receipt.
**Narration:** “A dense menu: sixteen regions, prices and times. The receipt shows the real
seconds and cost.”

### 2:25–2:50 — Honest limit (only if using demo fallback, say so)
**Shot:** label page; badge visible if demo.
**Narration:** “This is where it still fails: photographed labels. The editor is how you
take over — and a demo badge would mean this clip is a replay, not live.”

### 2:50–3:00 — Close
**Shot:** repo, README quickstart, tests.
**Narration:** “Naqsh runs from the public repo: clone, key, LIVE_MODE=1. Built with Muse
Spark, SAM 3.1 and Muse Image.”

## What NOT to say

- No time-saved ratio or “N× faster”; say **faster** at most.
- No “fully automatic”, “no editing needed”, “any language”.
- No “live” claim over a demo badge.
- No clean-plate success on the photo label.
- No slides.
