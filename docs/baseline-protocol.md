# Baseline protocol — manual localization vs Naqsh

Purpose: a **fair, repeatable** comparison of a human doing the same page by hand in
their normal editor against Naqsh's measured time. The ratio is reported per page and
is **PENDING** until this protocol has been run and the numbers are filled in.

No estimated numbers are allowed in the results table. If a step is skipped or the run
is interrupted, the run is invalid and is redone.

## Pages (fixed)

| Page | File | Regions | Why |
|---|---|---|---|
| Comic | `assets/generated/fixtures/01-comic-flat.png` | 3 | simplest page, least flattering to Naqsh |
| Menu | `assets/generated/fixtures/03-menu-paper.png` | 16 | dense text, prices, item+price layers |

Both are 1280×1920 in the pipeline's working copy. Use the same files, not screenshots
of the output.

## Setup

1. Editor you normally use for this work (name it and its version in the run log).
2. Screen recording on, whole screen, cursor visible, no cuts. If the recording fails,
   the run is invalid.
3. Open only the source page. **Do not look at Naqsh's output** for that page before or
   during the timed run; keep it closed.
4. Have the final files ready to save: a layered editable file and a flat PNG.

## Definition of "done" (timer stops here)

The output must be comparable in quality to Naqsh's for that page:

1. Every piece of lettering is replaced with Arabic; no English left.
2. Arabic is set right-to-left with correct joining, in a size that fits the original
   space.
3. The background behind the old lettering is cleaned — no ghost text, no obvious
   smear.
4. A layered file is saved with the text still editable, plus a flat PNG.

Stop the clock when both files are saved. Do not keep polishing after that point; if
the result is not comparable, the run is a **FAIL** and is redone, not extrapolated.

## Timed steps (record each)

| # | Step | Starts when | Ends when |
|---|---|---|---|
| 1 | Translate | you start reading/translating the page | the Arabic text is decided |
| 2 | Remove original lettering | you start masking/erasing | the plate is clean |
| 3 | Typeset Arabic | you start placing text | all lines are placed and fitted |
| 4 | Export | you start export | layered file + PNG are saved |
| — | **Total** | start of step 1 | end of step 4 |

Notes on fairness:

- Count decision time (font choice, fitting, second thoughts) inside the step it
  belongs to; do not pause the timer for thinking.
- Breaks are allowed but must be recorded and excluded from the total; state how long.
- Undo/redo counts as work time.
- No pre-translated text, no scripts, no batch actions that Naqsh users would not have.

## Run log (fill one row per page)

| Page | Date | Editor + version | Recorder | Step 1 | Step 2 | Step 3 | Step 4 | Total | Comparable? (Y/N) |
|---|---|---|---|---|---|---|---|---|---|
| comic | | | | | | | | | |
| menu | | | | | | | | | |

## Ratio

```
ratio = manual_total_minutes / naqsh_minutes
naqsh_minutes = receipt median for the same page (comic 33.8 s, menu 61.8 s)
```

Report the ratio **per page** and name the page. Never pool the two pages into one
number. Keep the region count beside each ratio. The table lives in
`docs/submission-notes.md` and stays PENDING until this protocol is run.
