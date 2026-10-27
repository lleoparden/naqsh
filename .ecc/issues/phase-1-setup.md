Phase 1 of the program in `docs/plan.md`. Setup and the Meta Model API smoke tests — no pipeline code.

## Goal

Prove the three models do what the pipeline needs before any product code depends on them, and stand up the repository the rest of the build lives in.

## Deliverables

- [x] Public repo with frontend/, backend/, docs/, assets/, README (with "what's new"), ASSETS.md, .env.example, .gitignore, docs/submission-notes.md
- [x] AGENTS.md and `.agents/workflows/` re-created for Naqsh (Vectr conventions learned read-only, no code copied)
- [x] `docs/plan.md` with phases, gates, fallbacks, submission as the last phase
- [ ] `smoke_spark_text.py` — text call, Arabic JSON shape, latency, cost
- [ ] `smoke_spark_image.py` — vision read: per-region bbox + source text + Arabic + style
- [ ] `smoke_sam.py` — streamed line, box fields, base85 mask decode, overlay PNG
- [ ] `smoke_image_generate.py` — rights-clean test panel
- [ ] `smoke_image_edit.py` — instruction-based lettering removal, artwork preserved?
- [ ] `docs/api-findings.md` filled with measured latency, cost, and any error
- [ ] `docs/submission-notes.md` friction log current

## Gate

Each model answers with the documented shape; SAM's payload decodes to `H×W` bits; the Image edit returns a usable image; every call's latency and cost is in the findings doc. Anything a probe cannot answer stays marked UNCONFIRMED.

## Evidence

Receipts under `backend/.cache/probes/` (gitignored) and the tables in `docs/api-findings.md`. Images: `assets/generated/test-panel.png` and its mask overlay.

## Non-goals

Pipeline stages, prompts beyond the probes, editor UI, export.

## Blocker

The owner is adding `MODEL_API_KEY` to `L:\naqsh\.env`; until then the paid probes do not run.
