# Step 0 — coverage-growth check (before Phase 3a)

2026-10-27, Cairo. Budget: $0.25; spent **$0.1927**.

## 1. Did the ten gate runs use the coverage-growth fix?

**Yes.** Every gate receipt records the segment stage as `box prompts + ink extent`,
a marker that only exists after `coverage.py` landed in `eaed06c`. Verified on all
ten jobs (`step0_check.py --verify`).

## 2. Fresh runs with the fix on

| Page | Runs | Detector residual | Cost | Time |
| --- | --- | --- | --- | --- |
| comic (flat) | 3 | none | $0.0247 / $0.0231 / $0.0251 | 45–50 s |
| menu (printed paper) | 3 | none | $0.0292 / $0.0446 / $0.0460 | 78–100 s |

**6/6 runs clean by the detector**, and the 100% crops (`step0-crops.png`) show no
ghost lettering on the comic.

## 3. Leader dots: still there, plainly

All three menu runs keep the **dotted leaders** between the dish and the price
(e.g. `كشري ........ 45`). The detector does not flag them, because they are
punctuation, not letters — the check prompt asks about lettering. So:

- this is a **known visual defect** on the menu page, not a plate regression;
- it is not in the demo's critical path for the comic, but the menu is a demo page.

Proposed fix (not built, per scope):

1. Ask the residual check about "leader dots / dotted runs" as a separate flag.
2. Detect them deterministically: small, evenly spaced round ink blobs on one
   horizontal band inside the repaint area, between two text blocks.
3. Remove them through the same routing (flat fill for paper, ink-inpaint for
   textured) and redraw the Arabic without leaders — a menu line does not need
   them once the price is right-aligned.

Until then: state the limit, or use the comic/chalkboard in the video instead of
the menu.

## Evidence

- `step0-runs.json` — jobs, costs, times, strategies
- `step0-crops.png` — 100% crops for every run
