# Phase 6 — layer editor and layered export

2026-10-27. What was built, what the numbers are, and what the owner must check by hand.

## Gate evidence

| Page | Layers after edits | Covers | SVG vs PNG mean diff | Pixels > 40 |
|---|---|---|---|---|
| comic (`6a8aa7a0829b`) | 4 (3 text, 1 cover) | 1 | **0.12** | 0.092% |
| menu (`e13f9585b24f`) | 11 (10 text, 1 cover) | 1 | **0.55** | 0.432% |

Edits applied through the API on real jobs: one line re-written (`… جدا`), one region retranslated to MSA (`في هذه الأثناء`), one SFX region skipped, one box nudged by (12, −8), one cover patch added. The exported SVG texts were verified to contain those exact strings.

- Editor screenshot: `gate-6a8aa7a0829b-editor.png`, `gate-6a8aa7a0829b-svg-render.png`
- Menu: `gate-e13f9585b24f-editor.png`, `gate-e13f9585b24f-svg-render.png`
- Round-trip: `verify.json` (XML parses; text/layer counts; ZIP has 4 fonts + 3 licence files; outlined variant has paths and **no** text elements)
- Gate numbers: `gate.json`

## Parity (server render vs browser SVG)

| Page | Mean abs diff | Pixels > 40 |
|---|---|---|
| comic | 0.36 | 0.29% |
| menu | 0.48 | 0.39% |
| chalkboard | 0.33 | 0.24% |

Differences are glyph-edge antialiasing; no line-break, order, or shaping differences observed. Method: the SVG is wrapped in HTML with the bundled fonts as `@font-face` and screenshotted in headless Chrome, then diffed against the server PNG.

## Data model

One JSON document per job: source size, plate/composite paths, page settings (`register`, `numerals`), and layers. Text layers carry `type`, `action` (translate / keep / skip), source text, Arabic per register, box, font, size, per-line baselines, colour, z, visible, locked. Cover layers carry a box and a flat fill. GET/PATCH `/api/jobs/{id}/document`, POST `/layout`, POST `/retranslate` (cost returned), POST `/cover`.

## Export design

- **Layered SVG**: viewBox = source pixels; plate embedded as a PNG data URL; cover rects; one `<text>` per line with `direction="rtl"`, `unicode-bidi="embed"`, `font-family`, `fill`; groups `plate`, `covers`, `text-layers`, `original-reference` (hidden); stable `id`s.
- **Outlined SVG**: same geometry with every glyph as a `<path>` (fontTools), so it looks right without the fonts but is not editable.
- **PNG**: exactly source dimensions.
- **ZIP**: both SVGs, plate PNG, the exact OFL fonts used, their licence texts, and a README explaining how to install the fonts. **Why bundle fonts:** SVG text names the family; without the font installed the browser substitutes and the Arabic breaks, so the editable file alone is not safe to hand over.

## What was NOT verified (owner checklist)

1. Open `export.svg` in Inkscape and Figma: are the text layers selectable and editable, do ids/names show, does the hidden reference group stay hidden?
2. Install the fonts from the bundle, reopen, and compare against `export-outlined.svg` — should look identical.
3. Click through the editor by hand (it was loaded and screenshotted headlessly, not clicked): select, edit text, re-translate, font/size/colour, drag/resize, cover drag, undo/redo, reload persistence.
4. Check that the cover patch at the top-left does not sit over anything the demo needs (it was placed deliberately for the gate).

The editor's drag, resize and cover tools are implemented but the automated evidence did not exercise mouse gestures; only API-level edits were driven.


## Hardening follow-up (2026-10-27)

- Dedupe on real reads: chalkboard 5 runs (5,3,3,5,3), PD poster 3 runs (8,8,8); no
  duplicates reproduced, so the synthetic tests are the only proof the rule fires.
- Text-only parity (union of text boxes, headless Chrome/Blink/HarfBuzz): comic 3.13
  mean / 2.57% over 40, menu 4.20 / 3.28, chalkboard 2.39 / 1.73.
- Editor click-through (Playwright, real mouse/keyboard): 10/10 interactions, see
  e2e.json and e2e-*.png.
