# English test suite + demo candidates

Data/tests only. No pipeline tuning was done for these pages; failures are reported as
they happened.

## Files

| Path | What it is |
|---|---|
| `fixtures/test-suite/manifest.json` | 13 pages: image, expected regions (`id`, `type`, `box`, `text`), features, expected `pass`/`fail`, generator note |
| `fixtures/test-suite/pages/*.jpg` | 10 Muse Image artworks with English text drawn in code (exact ground truth) + 3 pages whose text is rendered by Muse Image (curved, photo label, handwriting) and transcribed by hand |
| `backend/scripts/build_test_suite.py` | Regenerates the pages (paid: 13 × ~$0.01) |
| `backend/scripts/eval_test_suite.py` | Offline eval by default; `--live` requires `LIVE_MODE=1` and calls the API once per page |
| `docs/evidence/test-suite/*.json` | Cached live receipts/documents + `summary.json` |
| `backend/data/translation-cases.json` | 40 English strings |
| `backend/scripts/run_translation_cases.py` | Batch both registers, automatable checks, review sheet |
| `backend/scripts/build_demo_candidates.py` | 5 demo candidates, one live run each, contact sheet outside the repo |
| `frontend/e2e/demo-path-check.mjs` | Walks the demo script path in DEMO mode and reports wall time |

## Manifest format

```json
{
  "id": "menu-prices",
  "image": "pages/menu-prices.jpg",
  "expected": "pass",
  "features": ["prices", "3-4 digit numbers", "decimals", "times"],
  "regions": [
    {"id": "m1", "type": "menu_item", "box": [120, 340, 760, 430], "text": "SOURDOUGH 6.50"}
  ],
  "generator": {"images": "muse-image-1.0", "text": "code-drawn Inter", "prompt": "..."}
}
```

## Run

```bash
cd backend
python scripts/eval_test_suite.py                 # offline, cached
LIVE_MODE=1 python scripts/eval_test_suite.py --live   # paid, requires approval

python scripts/run_translation_cases.py           # paid ~$0.01, writes review sheet

# demo candidates (needs a LIVE_MODE=1 server on :8001)
python scripts/build_demo_candidates.py

# demo path (needs demo backend :8000 + preview :4174)
cd ../frontend && node e2e/demo-path-check.mjs
```

## Eval results (13 live pages, 2026-10-31)

- Cost: **$0.4296**; seconds **2.3–97.5 s**; cost/page **$0.0049–$0.0445**.
- Pass pages: recall **0.71–1.00**, mean **0.97**; CER **0.0–0.794**.
- Comic with 3 bubbles: 3 text, **3 bubble layers**, 93.0 s, $0.0436.
- Menu: recall **0.71** (2 price boxes unmatched), 57.8 s.
- Tiny-hours poster: 4 line-level regions for 1 expected block → **3 splits**, CER 0.794.
- No-text page: **0 regions**, 2.3 s, $0.0049.
- Expected-fail pages: curved headline (read correctly, but set straight in the editor),
  photo label (3 regions, 2 splits, CER 0.524), handwriting (3 regions, 2 splits, CER 0.706).

## Translation cases

- 40/40 returned in both registers; cost **$0.0105**.
- Arabic-script ratio **0.968–1.0** (Egyptian), **1.0** (MSA); length ratio **0.59–1.44**.
- Digits preserved: **38/40 Egyptian**, **37/40 MSA**; the failures add or drop number
  words (t15, t24, t33, t35, t36). No correctness is asserted; review sheet at
  `L:\naqsh-review\arabic-review\review.md`.

## Demo candidates

- Five pages (comic, bakery poster, cafe menu, honey label, night market), one live run
  each, background layers on.
- Runs: 71.1 s/$0.0459, 74.2 s/$0.0455, 45.2 s/$0.0251, 51.4 s/$0.0368, 93.6 s/$0.0450.
- Sources/results/contact sheet: `L:\naqsh-review\demo-candidates\`; manifest
  `docs/evidence/demo-candidates.json`. Owner picks 2–3.

## Costs

| Item | Cost |
|---|---|
| 13 suite images | $0.13 |
| 13 live eval runs | $0.4296 |
| 40 × 2 translation calls | $0.0105 |
| 5 demo images | $0.05 |
| 5 demo live runs | $0.1983 |
| **Total** | **$0.8184** of the $1.00 cap |

## Expected-fail rationale

- **Curved headline:** the reader can read it, but typesetting places Arabic on a straight
  line, so the visual result is wrong.
- **Photo label:** the plate cannot clean a photographed surface; smears/ghosts remain.
- **Handwriting:** the reader is inconsistent and the plate leaves marks.
