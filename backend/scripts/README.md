# Phase 1 API probes

One script per model. Each reads `MODEL_API_KEY` from the repo-root `.env` (or the
environment), makes the smallest call that answers its question, prints a compact
JSON summary, and saves the full response under `backend/.cache/probes/`
(gitignored). Receipts are how a paid call is reused instead of repeated.

| Script | Model | Question |
| --- | --- | --- |
| `smoke_spark_text.py` | Muse Spark | Does a text call return the requested Arabic JSON, and what does it cost? |
| `smoke_spark_image.py` | Muse Spark (vision) | Can it read regions in place and return bbox + Arabic + style as JSON? |
| `smoke_sam.py` | SAM 3.1 | Exact streamed line, box fields, mask encoding, decode to H×W bits, overlay PNG |
| `smoke_image_generate.py` | Muse Image | Generate the rights-clean test panel (`assets/generated/test-panel.png`) |
| `smoke_image_edit.py` | Muse Image | Can instruction editing erase lettering and keep the artwork? |

Run from the repo root:

```bash
python backend/scripts/smoke_image_generate.py          # do this first: it creates the test panel
python backend/scripts/smoke_spark_image.py assets/generated/test-panel.png
python backend/scripts/smoke_sam.py assets/generated/test-panel.png text
python backend/scripts/smoke_image_edit.py assets/generated/test-panel.png
python backend/scripts/smoke_spark_text.py
```

Notes:

- `smoke_sam.py` takes an optional second argument for the concept prompt
  (default `text`; try `speech bubble` if text regions come back empty).
- No script prints the key, and the receipts never contain it: the request is saved
  with the image data URL elided.
- A zero-match SAM response is valid and exits successfully with `objects: 0`.
