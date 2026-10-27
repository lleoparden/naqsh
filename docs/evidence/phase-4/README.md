# Phase 4 gate — clean plate

Run 2026-10-27, Cairo. Ten runs: two per fixture page, five pages with different
backgrounds. Code at commit `eaed06c` plus the timeout hardening in this PR.

## Result: **gate fails the 9/10 bar**

| Page | Runs clean by detector | My visual read (owner still judges) |
| --- | --- | --- |
| 01 comic (flat) | 2/2 | clean in both |
| 02 poster (watercolour) | 2/2 | **fails**: the plate flattens the painted band behind the text into a solid teal strip — a smear, even though no letters remain |
| 03 menu (printed paper) | 1/2 | 1 clean; the other keeps the leader dots under the Arabic (run 2, t9, inpainted) |
| 04 chalkboard | 2/2 | clean in both; chalk texture survives |
| 05 kraft label (photo) | 0/2 | **fails**: faint original word behind the Arabic plus a flat painted patch; residual reported on 3 regions (run 1) and 1 (run 2) |

Detector agreement: 7/10 runs with no text residual. It misses **smears** by
construction (it only answers "is there lettering"), so the visual pass rate is
lower than the detector's: roughly 5–6/10.

## Where the failures come from

1. **Ghost outside the old coverage** (fixed): residual ink sat outside the
   repaint area because the lettering was taller than Spark's box and the SAM mask.
   Coverage is now grown from the source's real ink extent.
2. **The plate flattens texture** (poster): Muse Image replaces a painted band with
   a flat colour. The composite faithfully copies that flat band, so it looks like a
   smear even though the edit "worked".
3. **Faint ghosts on photo stock** (label): the ghost is close to the local fill, so
   the flat-fill tolerance skips it, while the fill itself destroys the paper
   texture. Neither Muse nor flat fill is right here.
4. **Whole-coverage inpainting smears** (menu t9): Telea over a wide area invents
   texture; only thin-stroke inpainting preserves the surroundings (tested offline,
   not in these ten runs).

## Numbers

| Metric | Value |
| --- | --- |
| Runs / pages | 10 / 5 |
| Total cost | **$0.2975** |
| Cost per run | $0.0298 (range $0.0218–$0.0414) |
| Cost per page (2 runs) | $0.0595 |
| Wall time, 10 runs | 748 s (75 s/run, range 44–126 s) |
| Regions processed | 44 |
| Strategies | muse 23, muse-retry 16, flat-fill 4, inpaint 1 |

## Diagnosis numbers (step 1)

Saved failing runs, residual ink vs repaint coverage:

| Job | Inside coverage | Outside coverage |
| --- | --- | --- |
| a23796afc337 | 5,444 px | **6,894 px** |
| a664bea34d91 | 2,187 px | **4,314 px** |
| f377b49c8b48 | 3,202 px | **6,362 px** |

Registration offsets observed on the same page: **-16, -30, -40 px** vertical;
`dx = 0` every time, so the offset is vertical-only in practice. Scale is exactly
the source/plate ratio after resize. Ring residuals are in each job receipt.

## Fallback (from docs/plan.md)

- **Short term, demo-safe:** gate the video on the stylised pages (comic, menu,
  chalkboard) where the plate is reliable, and state the photographic limitation
  honestly. The demo page is flat art.
- **Plan B for textured pages:** thin-stroke inpainting (closing-based background
  estimate, inpaint only the strokes). Offline test on the label looked better than
  flat fill, but it is not in these ten runs and needs its own two-run check.
- **Plan C:** let the editor cover a region with a sampled patch — the user is the
  last resort for photographic stock, exactly as a letterer would be.

## Evidence files

- `contact-sheet.png` — every run, every region, 100% crops, labelled strategy.
- `gate-runs.json` — job ids, costs, times, strategies, detector verdicts.
- `gate-progress.log` — raw run log.
