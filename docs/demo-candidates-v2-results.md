# Demo candidates v2 — pre-filter results (2026-10-31)

Six flat-style pages (`fixtures/demo-v2/`), one live run each with background layers on.
PASS bar: recall **1.00**, CER **0.0**, under **60 s** (verify notes are separate).

| Page | Expected | Detected | Recall | CER | Seconds | Cost | Pass | Verify note |
|---|---|---|---|---|---|---|---|---|
| comic-bakery-flat | 4 | 4 | 1.00 | 0.0 | 61.8 | $0.0417 | **FAIL** (time) | bottom letter fragments under a cover bar |
| cafe-poster-flat | 2 | 2 | 1.00 | 0.0 | 56.4 | $0.0404 | **PASS** | lettering “visible, partially cropped” (flagged) |
| honey-label-flat | 3 | 1 | 0.33 | 4.6 | 32.4 | $0.0232 | **FAIL** | three lines read as one region |
| chalkboard-flat | 3 | 1 | 0.33 | 2.0 | 48.1 | $0.0384 | **FAIL** | three lines read as one region |
| postcard-flat | 2 | 2 | 1.00 | 0.0 | 63.9 | $0.0405 | **FAIL** (time) | black fragments at top |
| children-flat | 2 | 2 | 1.00 | 0.0 | 49.2 | $0.0385 | **PASS** | fragments along the top edge |

- Live cost **$0.2227**; images **$0.18** (two generations, one page regenerated once after a
  margin fix); **task total $0.4027 of $0.50**.
- Plate diff outside masks: **2.49–7.38** mean abs — the plate changes pixels outside the
  saved masks, worth a look (no pipeline change made).
- **No source-art regeneration:** the four failures are reading granularity (honey/chalk
  lines merged), time (comic/postcard) and ghost fragments, not the source style; only
  ~$0.10 of the cap remains and one regenerate+rerun is ~$0.05.
- All six, including failures, are in the labelled contact sheet:
  `L:\naqsh-review\demo-candidates-v2\contact-sheet.jpg` (source | result, one page per row).

## Blunt assessment

- **cafe-poster** and **children** pass the numeric bar but their verify notes still report
  cropped/top-edge fragments, so they may look imperfect.
- **comic** has perfect reading but is 61.8 s and leaves bottom fragments under a cover bar.
- **postcard** is 63.9 s with top fragments.
- **honey** and **chalkboard** fail because the three code-drawn lines are read as one
  region (recall 0.33); the Arabic is not the problem.
- The v2 style is flatter and the text is inside code-drawn containers, which fixes the v1
  “pasted on” look, but the time bar is not reliably met.

## Evidence

- Cached receipts/documents: `docs/evidence/demo-v2/*.json`, summary `summary.json`.
- Script: `backend/scripts/prefilter_demo_v2.py`.
- Pages/manifest: `fixtures/demo-v2/`.
- Cost ledger: `docs/evidence/api-spend.jsonl`.
