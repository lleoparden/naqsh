# Naqsh (نقش)

**Arabic-first visual localizer.** Upload a comic page, poster, or menu; Naqsh
reverse-engineers it into editable layers — text regions segmented, translated
into natural Arabic, the original lettering repainted away, and the Arabic
re-typeset right-to-left in the original style — then lets you fix any region in
a layer editor and export a layered, editable SVG or a flat PNG.

Most localization tools treat right-to-left text as an afterthought: mirrored
layouts, broken ligatures, Latin fonts forced onto Arabic, no way to nudge a line
that overflows a speech bubble. Arabic creators, small publishers, and small
businesses still localize by hand. Naqsh is built for them first.

> **Status (2026-10-27):** Phase 1 — setup and Meta Model API smoke tests. The
> pipeline described below is the target; this repo currently contains the
> scaffold, the API probes, and the evidence they produce. See
> [`docs/plan.md`](docs/plan.md) for the phase plan and go/no-go gates.

## What's new / built during the hackathon

This repository is **new work written during the Meta Global AI Developer
Hackathon (Oct 26 – Nov 4, 2026)**. It is not a fork, a port, or a rebrand of an
older project. In particular:

- No code, assets, brand, or configuration was copied from the author's earlier
  desktop design tool (Vectr). None of that project's Electron shell, Skia
  renderer, document format, compiler, release pipeline, or branding appears
  here. Its *workflow conventions* (branching, commit style, issue/PR habits,
  agent instruction files) were re-created from scratch for Naqsh.
- Every file in this repo was authored during the event. The first commit is the
  repo scaffold; the history shows the build as it happened.
- Only assets with clear rights are used: CC0/public-domain media, or images
  generated with Muse Image. Every asset and its license is recorded in
  [`ASSETS.md`](ASSETS.md).

## The pipeline

1. **Upload** — any page image (comic page, poster, menu).
2. **Segment** — SAM 3.1 finds text regions, speech bubbles, objects, background.
3. **Read + translate** — Muse Spark reads each text region, translates it into
   natural Arabic, and identifies the lettering style.
4. **Clean the plate** — Muse Image repaints the background where the original
   text was.
5. **Re-typeset** — Arabic is set right-to-left in a matching style and fitted to
   each region (bubble-aware wrapping, no clipped ascenders or diacritics).
6. **Edit** — a layer editor (the centerpiece of the UI) lets the user fix text,
   position, font, and size per region.
7. **Export** — layered, editable SVG and PNG.

## Why Meta's models

| Model | Role in Naqsh | Why it can't be swapped trivially |
| --- | --- | --- |
| **SAM 3.1** | Pixel-accurate text/bubble/object masks | Mask geometry with stable object ids, streaming, and base85 masks — the layer boundary comes from here, not from a bounding box guess. |
| **Muse Spark** | Reads text in place, translates to Arabic, names the style | Vision + multilingual register control in one call; the translation must fit the bubble, so we ask for both at once. |
| **Muse Image** | Removes original lettering, repaints the plate | Instruction-based editing that preserves the rest of the artwork; no mask parameter, so Naqsh composites the result back through SAM's masks. |

## Stack

- **Frontend:** React + Vite + TypeScript + Tailwind
- **Backend:** Python + FastAPI
- **Models:** Meta Model API (`https://api.meta.ai/v1`) — Muse Spark, Muse Image,
  SAM 3.1

## Repository layout

```
backend/            FastAPI service + API probes
  app/              service code
  scripts/          one smoke-test script per Meta model
  tests/            pytest
frontend/           Vite + React + TypeScript + Tailwind app
docs/               plan, API findings, submission notes, decisions
assets/             rights-cleared media (see ASSETS.md)
.agents/workflows/  agent workflows: issue readiness, feature tracing, planning
.ecc/issues/        program index and issue bodies as they are filed
```

## Local setup

```bash
# backend
cd backend
python -m venv .venv && .venv/Scripts/activate    # Windows
pip install -r requirements.txt
cp ../.env.example ../.env                         # then paste your key
uvicorn app.main:app --reload --port 8000

# frontend
cd frontend
npm install
npm run dev
```

## API probes

Each probe is standalone, prints a compact JSON receipt, and writes raw output
under `backend/.cache/probes/` (gitignored):

```bash
python backend/scripts/smoke_spark_text.py
python backend/scripts/smoke_spark_image.py assets/generated/test-panel.png
python backend/scripts/smoke_sam.py assets/generated/test-panel.png
python backend/scripts/smoke_image_generate.py
python backend/scripts/smoke_image_edit.py assets/generated/test-panel.png
```

Results, request/response shapes, latency, cost, and every failure are recorded in
[`docs/api-findings.md`](docs/api-findings.md).

## Rights

Code: see [`LICENSE`](LICENSE). Media: see [`ASSETS.md`](ASSETS.md). No
copyrighted comics, manga, or Webtoon material is used anywhere in this project.

## Submission

Meta Global AI Developer Hackathon — Track: Indie Developer, solo.
Problem statement: *Build for Your World*. Team: Naqsh (Mostafa Eid).
Submission checklist and living notes: [`docs/submission-notes.md`](docs/submission-notes.md).
