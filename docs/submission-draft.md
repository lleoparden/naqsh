# Submission draft

Working draft for the Meta Global AI Developer Hackathon form. Every number below
points at the receipt or file it came from. The manual-baseline ratio is **not**
claimed — that column is still empty (`docs/time-saved.md`).

## Project

**Naqsh (نقش)** — an Arabic-first localizer that turns a comic page, poster or menu into
editable, translated layers.

## Short description

Upload a page. Naqsh finds every piece of lettering, translates it into natural Arabic,
repaints the artwork cleanly, sets the Arabic right-to-left in the original space, and
opens a layer editor where every line can be fixed and exported as a layered SVG or PNG.

## Long description

Localizing a page into Arabic is still hand work: someone masks each line, repaints the
background, translates, picks a font that supports Arabic shaping, and re-exports. Naqsh
does the first pass and leaves every decision editable.

The pipeline: Muse Spark reads and translates the page; SAM 3.1 segments each text
region; Muse Image repaints a clean plate; the plate is registered back onto the
original and composited only inside the text masks; HarfBuzz/FreeType set the Arabic
with real shaping and fitted line breaks; a second Spark vision pass checks the render
and can fix one round; the layer editor exposes text, register, font, size, colour,
position, visibility, z-order and manual cover patches; export produces a layered SVG
(real `<text>`), an outlined SVG fallback, a PNG at source size, and a ZIP with the
exact OFL fonts and licences.

Measured on live runs, not estimates:

- Comic page (1280×1920, 3 regions): **median 33.8 s** (28.5–37.4), **$0.0257–$0.0291**,
  over 3 post-change runs (`docs/evidence/phase-8/variance-summary.json`).
- Menu page (16 regions after item/price splits): **median 61.8 s** (61.5–78.5),
  **$0.0367–$0.0661**, over 5 post-change runs (`docs/evidence/phase-8/variance-summary.json`);
  an earlier post-change pair took 89–122 s (stated in the variance PR, not saved to JSON).
  The same page took a median **181.1 s** before the speed work
  (`docs/evidence/phase-7/live-runs.json`).
- The local stage that dominated the menu went from **56.3 s to 3.7 s** (register +
  coverage) with pixel-identical output on three stored jobs, and menu
  `register_composite` from a **75.7 s median to 1.8 s**
  (`docs/evidence/phase-8/profile.json`, `docs/evidence/phase-8/morph-equivalence.json`,
  `docs/evidence/phase-8/variance-summary.json`).

Honest limits, stated because they are in the evidence: photographed/painted surfaces
can defeat the plate (the kraft-label run shows brown smears, cached as `label-fail` in
`fixtures/demo/`); curved/rotated headlines are read but set as a straight line; about
0.4% of pixels differ between the browser and server renders of the same SVG
(`docs/evidence/phase-6/parity.json`).

## Use of Meta products

| Product | What it does in Naqsh | Evidence / numbers |
|---|---|---|
| **Muse Spark (vision)** | Reads every lettering region, its box, type and style; self-check pass over the rendered page | Recall **1.00 on all 8 fixtures**, precision 0.88–1.00 (`docs/evidence/phase-5/recall-eval.json`); self-check on injected faults caught **11/12 (91.7%)**, class right 8/12, **0/6 false positives** (`docs/evidence/phase-3/selfcheck.md`) |
| **Muse Spark (text)** | Translates each line, Egyptian and MSA registers; repairs a translation only when the self-check asks | Typesetting gate: 6 runs / 23 regions, **0 overflow**, $0.1823 (`docs/evidence/phase-3/typeset-gate.md`) |
| **SAM 3.1** | Segment masks from box prompts, streamed as special-token text and decoded to masks | Masks drive every layer boundary and the composite; per-region coverage is built from the real ink extent (`backend/app/pipeline/coverage.py`) |
| **Muse Image (edit)** | Repaints a clean plate with the lettering removed (no mask parameter) | The plate is registered and composited through masks, so only masked pixels come from the model (`backend/app/pipeline/plate.py`) |

Model roles and the API shapes are recorded in `docs/api-findings.md`.

## Why Meta's models matter

- **Spark's vision reading is the entry point.** It returns boxes, text, type and style
  in one call; without it every region would need manual boxing.
- **Spark's text call is the translator and the repair loop.** The self-check uses the
  same model family to look at its own render and request one fix, which is how clipping
  and overflow get caught without a human.
- **SAM is what makes "layers" real.** The masks are the layer boundaries, the repaint
  area and the export geometry.
- **Muse Image is the only component that can invent clean background pixels.** Prompt-only
  editing is imperfect, which is why Naqsh registers and composites instead of trusting
  the whole re-render.
- **Cost is low enough to iterate.** The comic page (3 regions) costs
  **$0.0257–$0.0291** and the menu page (16 regions) **$0.0367–$0.0661** in the live
  receipts (`docs/evidence/phase-8/variance-summary.json`), so a user can run the first
  pass without thinking about it.

## Optional feedback on Meta products

All observed during this build; details in `docs/api-findings.md`.

- **SAM 3.1 box prompts need a frame prefix.** A box prompt is only honoured after
  `<0f>id`, and the mask comes back as base85 text with its own H/W and encoding marker —
  workable once known, easy to get wrong from the docs alone.
- **Muse Image edit has no mask parameter.** Every edit re-renders the whole page, which
  lands with a global offset (about 16 px on our runs, sometimes 30–40 px), so the client
  has to register and composite through masks. An inpainting/mask input would remove a
  whole failure class.
- **A concept prompt with an empty result is still billed.** One probe spent tokens for a
  concept prompt that returned nothing.
- **No cost field in responses we saw.** Costs had to be recomputed from usage tokens and
  published prices; the probe receipts now carry a `cost_usd` backfilled from usage.
- **Rate/latency variance is high** (menu 61–122 s on the same code), so a recording or
  demo needs a replay mode; ours is labelled on screen.

## Links and status

- Repository: `https://github.com/lleoparden/naqsh` (public; no secrets — audit in
  `docs/audit.md`).
- Demo video: **not recorded yet**; the recording plan and the one-live-run rule are in
  `docs/recording-guide.md`.
- Impact claim: the time-saved ratio is **pending** the owner's manual baseline
  (`docs/time-saved.md`); no ratio is claimed here.
- Live runs used for the numbers above were made on 2026-10-27 with `DEMO_MODE=0`; demo
  mode replays real cached runs and is labelled in the UI.
