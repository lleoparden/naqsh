# Submission — final package (2026-10-31)

Every number is a range from the cited receipt; no time-saved ratio is claimed (owner
decision 2026-10-29). Live URL is **not required** (organizer answer 2026-10-31).

## Form fields

| Field | Value |
|---|---|
| Team name | **Naqsh** |
| Team member | Mostafa Eid (Lleoparden) |
| Track | Indie Developer |
| Problem statement | Build for Your World |
| Public repo | `https://github.com/lleoparden/naqsh` (public, MIT) |
| Demo video | 3:00 English, live-first; link to be added when recorded |
| X post link | to be added before the deadline |
| Hosting | **not required**; no deployment |

## One-paragraph description

Naqsh is an Arabic-first visual localizer: upload a comic page, poster or menu; Muse Spark
reads and translates the lettering, SAM 3.1 segments it, Muse Image repaints the plate,
Arabic is typeset right-to-left, and a layer editor exposes scenery, bubbles and text for
editing before layered SVG/PNG/ZIP export.

## How judges can run it

Follow **README → “Quickstart for judges”**: clone, Python venv + `pip install`, Node
`npm install && npm run build`, put `MODEL_API_KEY` in `.env` (a payment method is required
at dev.meta.ai), then run the backend with `LIVE_MODE=1` and the preview server.
Demo mode (`DEMO_MODE=1`, `LIVE_MODE=0`) replays recorded runs with a visible badge and
needs no key; it is a fallback, not the main path. Offline tests: `pytest -q`,
`npm run typecheck && npm run build`.

## Measured numbers (ranges, cited)

| What | Range | Source |
|---|---|---|
| Comic page, live | **≈ 29–62 s; $0.026–0.040** | demo receipt $0.0280/39.8 s; fresh-clone runs 48.7 s/$0.027682 and 61.7 s/$0.039521 (`docs/evidence/live-ui-fresh-clone.json`, `docs/evidence/fresh-clone-2026-10-31.md`); variance `docs/evidence/phase-8/variance-summary.json` |
| Menu page, live | **≈ 62–122 s; $0.037–0.066** | `fixtures/demo/menu/receipt.json` (90.3 s/$0.0391); variance `docs/evidence/phase-8/variance-summary.json` |
| Demo candidates v2 | 32.4–63.9 s; $0.0232–$0.0417 | `docs/evidence/demo-v2/summary.json` |
| Recall (English suite, pass pages) | 0.71–1.00, mean 0.97 | `docs/evidence/test-suite/summary.json` |
| Read CER | 0.0–0.794 | same |

Waits are wall-clock; video takes may cut them with an on-screen “sped up”/“cut” label.

## Use of Meta products

Muse Spark vision reads/checks, Muse Spark text translates, SAM 3.1 segments, Muse Image
repaints. Muse Image outputs are allowed with no on-screen credit (organizer answer
2026-10-28, Discord #questions); prompts/model/source are in `ASSETS.md`.

## Honest limits

Photographed/painted textures can defeat the plate (`fixtures/demo/label-fail/`); curved
headlines are read but set straight; about 0.4% of browser-vs-server SVG pixels differ
(`docs/evidence/phase-6/parity.json`). No time-saved ratio.

## What is still open

- Record the live-first 3:00 video and add its link.
- Post on X and add the link before the deadline.
- Outside AI coding tools remain PENDING; it does not change the repo or the video.
