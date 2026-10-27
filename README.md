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

> **Status (2026-10-27):** end-to-end pipeline, layer editor, layered SVG/PNG export and
> a labelled demo replay mode are in place. Latest post-change live measurements:
> **comic median 33.8 s (28.5–37.4), $0.0257–$0.0291, n=3** and **menu median 61.8 s
> (61.5–78.5), $0.0367–$0.0661, n=5** — per-run receipts in
> [`docs/evidence/phase-7/`](docs/evidence/phase-7/) and
> [`docs/evidence/phase-8/`](docs/evidence/phase-8/). The clean plate is still
> intermittent on photographed surfaces — see the Phase 4 gate in
> [`docs/plan.md`](docs/plan.md) and the honest-limit run
> `fixtures/demo/label-fail/`.

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

### What runs today

`POST /api/localize` (multipart `image`, form `register=egyptian|msa`) executes:

| Stage | Module | Call |
| --- | --- | --- |
| read | `app/pipeline/regions.py` | Muse Spark vision → regions JSON |
| segment | `app/pipeline/segment.py` | SAM 3.1 box prompts → per-region masks |
| clean_plate | `app/pipeline/plate.py` | Muse Image edit → plate |
| register_composite | `app/pipeline/plate.py` | phase correlation + masked composite |
| typeset | `app/pipeline/typeset.py` | arabic-reshaper + bidi, ink-aware fitting |
| render | `app/pipeline/render.py` | draw Arabic over the plate |

Every stage reports its own wall time and cost in the job receipt
(`backend/.cache/jobs/<id>/job.json`). Artifacts are served at
`/api/jobs/<id>/files/<name>`; `docs/evidence/phase-2/` holds the committed
before/after pair.

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
docs/               plan, API findings, submission notes, decisions, evidence/
fixtures/demo/      cached real runs for DEMO_MODE replay (see ASSETS.md)
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

## Demo mode (recorded replays)

Recording the video on the live API means waiting on model latency and rolling the
dice on every take. `DEMO_MODE=1` replays **real cached runs** for five known
fixtures — comic, menu, chalkboard, SFX comic, and the failing kraft label — with the
original receipt untouched: same per-stage milliseconds, same cost. Nothing is
pre-generated or shortened.

```bash
# backend with replay on (the cached runs need no API key)
DEMO_MODE=1 uvicorn app.main:app --port 8010
```

- A byte-for-byte match for a cached fixture is replayed; **anything else goes live**.
- The UI always shows a **“Demo mode: replaying recorded run”** badge; it cannot be
  hidden by `?clean=1`.
- Re-translate replays the cached Egyptian/MSA line, with cost $0 and no model call.
- Turn it off by unsetting `DEMO_MODE` (or `DEMO_MODE=0`) and restarting the backend.
- The cache lives in `fixtures/demo/` (receipt, document, plate, source, masks);
  rebuild it from the recorded jobs with `python backend/scripts/build_demo_cache.py`.
- **Honest-use rule:** the final video must include at least one live run.

Recording checklist: [`docs/recording-guide.md`](docs/recording-guide.md).

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
