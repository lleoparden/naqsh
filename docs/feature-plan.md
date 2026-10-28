# Feature plan — after the demo

Feature freeze: **1 Nov 2026**. This file scopes what comes after the hackathon build.
Effort figures are **estimates** and labelled as such. Costs per page come from the live
receipts (comic $0.0257–$0.0291, menu $0.0367–$0.0661).

Ranked against the rubric: **Impact 30 · Meta tooling 25 · Demo 25 · Technical depth 20**.

## Priority order

### A. Chapter batch mode (highest impact)

**User value.** A creator localizes a chapter, not a page. One ZIP in, one ZIP out, with a
shared glossary so names, places and SFX read the same on every page. This is the single
biggest time saver for the comic audience and the clearest product story.

**Pipeline/UI change.** Batch queue over `run_page_job` with per-page isolation; a job-level
glossary (source term → Arabic) injected into the translation prompt and validated after
read; ZIP input unpacking with page ordering; a batch review screen that reuses the editor
pane per page; export one ZIP with per-page folders and the glossary file.

**Numeric gate.** A 10-page chapter completes with **≥95 % of glossary terms applied
exactly**, **no cross-page state leak** (page order and IDs preserved), and total time
reported per page. Fallback if the gate fails: batch upload only, no glossary.

**Cost per page.** Unchanged (same model calls) → **$0.026–$0.066/page**; a 10-page chapter
≈ **$0.30–$0.60**.

**Risks.** Long jobs need resumability; partial failures must not lose completed pages;
glossary may fight natural phrasing; memory if pages are held together.

**Effort estimate: 24–32 h.**

### B. Layers-only mode (translation off)

**User value.** Designers and publishers who want the layers and clean plate without
translation: same page, English text layers, masks, layered export. Also a trust-building
demo (“it understands the page”) and a cheaper entry point.

**Pipeline/UI change.** A mode flag that skips translate, re-translate and Arabic typesetting;
keep read, segment, plate, composite; text layers carry `source_text` only and export uses
the original language with the original font stack; editor hides Arabic-only controls.

**Numeric gate.** Same recall as today (≥1.00 on the fixtures), text unchanged
character-for-character from the read step, layered export round-trips, no Arabic-specific
calls in the receipt. Fallback: hide the mode behind a flag and ship Arabic-only.

**Cost per page.** Drops by the translation/self-check calls: expect **$0.020–$0.035**.

**Risks.** Lettering style matching for Latin fonts is weaker than Arabic; export font
availability for Latin originals.

**Effort estimate: 12–16 h.**

### C. Extra RTL targets — Persian, Hebrew, Urdu (experimental)

**User value.** Same visual-localization problem in three more RTL markets; Persian is the
closest to Arabic typographically.

**Pipeline/UI change.** Language pack per target: prompt/register, direction, font set
(Persian: Vazirmatn; Hebrew: Noto Sans Hebrew; Urdu: Noto Nastaliq), digit handling,
per-language QA. Shaping already HarfBuzz; the fitter needs per-script metrics.

**Numeric gate.** One page per language, **native review** of 10 lines per language, zero
overflow, correct joining. Plus the requested test: *does any source language already read
correctly into Arabic?* — e.g. Persian/Urdu source text read as Arabic script must not be
silently “translated” into wrong Arabic; record the failure rate on a 10-line sample.
Fallback: label **experimental** and keep Arabic-only in the UI.

**Cost per page.** Similar to Arabic, **$0.03–0.07**; plus native review time.

**Risks.** Font licensing and shaping quality (Nastaliq is hard); native review cost; the
Arabic-first brand becomes diluted.

**Effort estimate: 20–30 h.**

## Ranking and cut order

| Feature | Impact | Meta tooling | Demo | Technical depth | Do first? |
|---|---|---|---|---|---|
| A batch + glossary | High | Medium | High | High | 1 |
| B layers-only | Medium | Low | Medium | Medium | 2 |
| C extra RTL | Medium | Medium | Low | High | 3 |

Cut order if time runs out: **C first**, then the glossary part of A (ship batch without a
glossary), then B. Do not cut the single-page editor/export path; it is the demo.

## What is explicitly out of scope

Logo, mascot, app renaming (owner decisions, not scheduled), multi-user accounts, billing,
mobile layout, and any hosted deployment until the live-URL answer is confirmed.
