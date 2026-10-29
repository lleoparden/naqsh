# After-side offset — cause and fix

Date: 2026-10-29. Owner reports an ~8 px vertical offset on the after side at the
before/after divider, while exported pixels match.

## Reproduction

With a real comic job at exactly 100 % zoom (1:1 screenshots, 1280×1920), the **source**
frame line sits at y=299 and the **composite** frame line at y=294 (5 px higher) across
the title area; at split 50 the left (original) and right (after) frame edges differed by
4–5 px. Screenshots: `L:\naqsh-review\offset\split-50.png`, `split-50-crop.png`,
`after-split-0.png`, `export.png`.

## Root cause

1. The title region's SAM mask includes the panel frame: `mask-t1` bbox starts at y=303,
   while the frame line is at y=299.
2. Coverage (the area replaced by the cleaned plate) was built from the mask **plus** the
   reading box and an ink-extent search with a 72 px pad, so it covered the frame line.
3. Muse Image's repaint redrew the caption box/frame a few pixels higher (plate frame at
   y=294, or y=285 on another generation). The composite therefore took the shifted frame
   from the plate, moving the after side while the original stayed put.
4. Export matched the composite, so pixel diffs against the export could not see it; the
   visible offset was between the original and the repainted background.

## Fix

- `coverage_for` now anchors the ink search to the **SAM mask bbox** (8 px pad) instead of
  the reading box ±72 px, so a nearby frame line is not pulled into the repaint area.
- `plate.composite` protects **long straight dark lines** (panel borders/frames) from both
  the source and the plate: those rows/columns (±6 px) are restored from the source, so a
  shifted redraw can never move the frame.
- Regression tests: synthetic frame 21 px above the mask stays put; a frame inside the
  mask also stays put when the plate is shifted 5 px.

## Verification

- Synthetic tests pass (`tests/test_coverage.py`, 8 tests).
- Offline recompute on the real job `5313ddafca2e` (plate + masks from a live run):
  source frame y=299, composite after the final fix y=299 at x=200, 280, 320, 400, 500,
  700. Before the fix it was y=285–294.
- **Not live-verified after the final union-of-lines change**: the two live comics
  (37.2 s / $0.0294 and 69.9 s / $0.0401) were run before that last tweak, and the
  remaining $0.10 task cap could not cover another run. The code path used offline is the
  same `composite()` call; only the pipeline wrapper is untested live.

## Limits

- The existing demo cache still contains the old composites; rebuild it before recording
  the before/after divider close-up.
- Line protection restores source on any row/column whose dark pixels exceed 45 % of the
  page; unusually dark full-width illustrations could keep original pixels there.
