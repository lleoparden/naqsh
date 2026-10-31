# Submission notes — living document

Update this **as work happens**. It feeds the submission form, the demo video
script, and the X post. Every claim here should be something we can show.

Submission form: Cerebral Valley platform, one per project. Deadline **4 Nov
2026, 9:00 PM ET** (≈ 4:00 AM 5 Nov Cairo). Internal submit date: **3 Nov**.

## Form fields — current state

| Field | Status | Content / where it lives |
| --- | --- | --- |
| Team name | ready | **Naqsh** |
| Team member | ready | Mostafa Eid (Lleoparden) |
| Track | ready | Indie Developer |
| Problem statement | ready | Build for Your World |
| Most Viral Track (X post link) | pending | Build-in-public clip; media folder below |
| Project description | draft | README pitch; tighten to ~150 words for the form |
| Public GitHub repo | in progress | `https://github.com/lleoparden/naqsh` (public) |
| 3-minute demo video | pending | Script outline below; backup target 30 Oct |
| Use of Meta products | draft | Model roles table below |
| Why Meta's models matter | draft | Below — what each model does that another tool couldn't |
| Feedback on Meta products | collecting | Friction log below |
| Feedback on partner technologies | optional | — |

## What each Meta model does, and why it mattered

Fill this in with *observed* behavior, not the pitch.

- **SAM 3.1 — geometry.** Turns "find the lettering" into pixel-accurate masks with
  stable object ids. Why it mattered: the layer boundary is the real bubble shape,
  so Arabic can be fitted to it instead of a guessed rectangle. *(Observed: a
  two-word concept prompt found both speech bubbles at 0.96 confidence, and a box
  prompt tightened a caption region to the panel edge. A `text` concept prompt found
  nothing — the model is prompted with objects, not "text", which is why Spark's
  boxes drive it.)*
- **Muse Spark — reading and rewriting.** One call returns the source text, its
  position, a natural Arabic line, and a lettering style. Why it mattered: the
  translation must fit the space, so text and style are decided together; a
  text-only pipeline would need OCR + translator + classifier. *(Observed: 3/3
  regions read exactly, valid JSON, and `أشوفك بكرة وهجيب معايا الرسومات` for "See
  you tomorrow, I'll bring the sketches" — proper Egyptian colloquial.)*
- **Muse Image — repainting the plate.** Removes the original lettering while
  keeping the artwork. Why it mattered: without it Naqsh could only cover lettering
  with flat boxes. *(Observed: all three text regions erased in 13.6 s for $0.01,
  bubbles left empty and the character unchanged — but the whole page is re-rendered
  with a vertical offset that varies per run (-16, -30, -40 px measured), so the
  plate must be registered before compositing.)*
- **Muse Spark as the QA loop.** The same vision model that reads the page also
  checks the cleaned plate at 100% zoom and reports which regions still show
  lettering. Why it mattered: a pixel threshold could not separate clean from
  ghosted plates, but the model can look. *(Observed: it caught residual text in
  7/10 regions on the dense menu page that the threshold missed; one retry then
  cleared them.)*

## API friction log (write it when it happens)

| When (Cairo) | What | Detail | Impact |
| --- | --- | --- | --- |
| 2026-10-27 15:20 | Reachability | `GET /v1/models` and `POST /v1/chat/completions` return 401 over HTTPS from Cairo; no timeout, no geo-block at the network layer. | Good — no VPN needed. |
| 2026-10-27 15:40 | Muse Image has no mask parameter | Multipart `mask` returns `400 unsupported_parameter`; edits are instruction-only. Docs also do not promise geometry preservation. | Design change: composite edit output through SAM masks (Plan A), classical inpaint (Plan B), opaque cover (Plan C). |
| 2026-10-27 15:40 | SAM output is special-token text | Masks are compressed base85 payloads inside `<|mask;...|>` tokens, one `output_text` line per frame, streamed. A hand-built decoder fails; `meta-sam-parser` decodes it. | One dependency, and the mask raster is the size of the object's box, not the page. Budgeted an hour; it took about that. |
| 2026-10-27 15:36 | Reasoning tokens ate the answer | With `max_output_tokens: 400`, Spark returned `status: incomplete` and **398 of 400 output tokens were reasoning** — an empty answer that looked like a JSON bug. | Two wasted calls; fix is `reasoning.effort: minimal` + a realistic token budget. Worth saying in the Meta feedback. |
| 2026-10-27 15:37 | SAM concept prompt `text` finds nothing | 0 matches, 200 OK, empty lane, still billed. `speech bubble` found both bubbles. | Region strategy: Spark bboxes → SAM box prompts, concepts only for containers. |
| 2026-10-27 15:39 | Box prompt syntax is not obvious | `<|box;…|>` alone → `400 invalid prompt: … geometric prompts go after a <Nf> frame header`. | Correct form: `<0f>1<|box;…|>` with caller-chosen ids. Docs describe it; the error message is what made it stick. |
| 2026-10-27 15:38 | Muse Image edit shifts the page | Phase correlation on before/after: ≈ -16 px vertical on the first pair, later runs -30 and -40 px. | Registration is required and is per-run, not a constant. |
| 2026-10-27 16:00 | Plate edits are intermittent | 7 runs: 4 clean, 2 with a faint ghost, 1 with a smeared caption panel. | Phase 4 gate owns this. The composite is correct; the ghost is in the plate. |
| 2026-10-27 16:20 | The ghost is mostly *ours*, not the model's | Comparing three failing runs, residual lettering sat outside the repaint coverage (e.g. 6,894 px outside vs 5,444 inside): the original lettering was taller than Spark's box and the SAM mask. | Coverage now grows from the source's real ink extent; the plate itself was clean in those runs. |
| 2026-10-27 16:35 | dirty_ratio cannot be trusted | Clean ≈0.05, ghosted 0.08–0.13, with overlap; a threshold retry doubled cost without reliably fixing the page. | Detection moved to a Muse Spark vision check over 100%-zoom crops. |
| 2026-10-27 17:00 | The plate flattens painted texture | Watercolour poster: the edit replaced the painted band behind the title with a solid teal strip. No letters left, but it reads as a smear. | Detector only asks about lettering, so it passed this. Textured pages are the open limit. |
| 2026-10-27 17:55 | فلالفل was my misreading, not the model | Search of every job receipt found no `فلالفل`; the recorded MSA translation is `فلافل 20`. The misspelling came from reading a downscaled contact sheet. | No pipeline bug: `_strip_leaders` only removes dots, shaping never rewrites the string. Added tests and a standard-spelling line in the prompt as a guard. |

## Notable results and numbers

| Date | Number | How it was measured |
| --- | --- | --- |
| 2026-10-27 | API reachable from Cairo, first byte < 1 s (401 response) | `Invoke-WebRequest` timing during the reachability check |
| 2026-10-27 | Spark vision read: 6.8 s, 3,367 in / 435 out tokens, **$0.00606** | Probe receipt `spark-image-20261027T123659Z.json` |
| 2026-10-27 | Spark Arabic line: 2.0 s, 137 in / 268 out (204 reasoning), **$0.00131** | Probe receipt `spark-text-20261027T123630Z.json` |
| 2026-10-27 | SAM bubbles: 3.4 s, 2 masks, conf 0.961, **$0.0025** | Probe receipt `sam-20261027T123816Z.json` + overlay PNG |
| 2026-10-27 | Muse Image generate: 12.2 s, 1280×1920 out for a 1024×1536 request, **$0.01** | Probe receipt `image-generate-20261027T123645Z.json` |
| 2026-10-27 | Muse Image edit: 13.6 s, lettering gone, **$0.01**, ≈16 px page shift | `image-edit-…json` + local phase-correlation measurement |
| 2026-10-27 | **Phase 2 pipeline, `01-comic-flat` (3 regions): 25–30 s, $0.0184–$0.0194** — historical, superseded by the live medians below | Per-stage receipts in `docs/evidence/phase-2/receipt-egyptian.json` |
| 2026-10-27 | Register comparison, same page | Egyptian `عيش طازة؟` / `كل يوم الصبح` vs MSA `خبز طازج؟` / `كل صباح` — same layout, same cost |
| 2026-10-27 | Clean-plate reliability: 4/7 runs clean, 2 ghosted, 1 smeared | Visual review of `docs/evidence/phase-2/failure-ghost-lettering.png` |
| 2026-10-27 | **Phase 4 gate: 10 runs / 5 pages, $0.2975 total, $0.0298 per run, 75 s per run** | `docs/evidence/phase-4/gate-runs.json` |
| 2026-10-27 | **Gate fails 9/10:** detector 7/10 clean; poster 2/2 flat-band smear, label 2/2 ghost+patch, menu 1/2 leader dots | `docs/evidence/phase-4/README.md` + contact sheet |
| 2026-10-27 | HarfBuzz typesetting gate: 6 runs (comic, menu, chalkboard × Egyptian/MSA), **0 overflow**, $0.1823 | `docs/evidence/phase-3/typeset-gate.md` |
| 2026-10-27 | Step 0: 6 repeat runs on comic/menu, 6/6 clean by detector; menu keeps leader dots | `docs/evidence/phase-3/step0.md` |
| 2026-10-27 | Spark self-check, injected faults: **11/12 caught (91.7%), 8/12 correct class (66.7%), 0/6 false positives**, $0.0108 | `docs/evidence/phase-3/selfcheck.md` |
| 2026-10-27 | Self-check on real pages: 0 flags, ~$0.002/page extra, no fix pass triggered | receipts from the comic/menu runs |
| 2026-10-27 | UI language toggle: EN default, AR mirrors; screenshots committed | `docs/evidence/phase-3/ui-toggle.md`, `ui-en.png`, `ui-ar.png` |
| 2026-10-27 | **Phase 5 recall: 1.00 on all 8 fixtures**; precision 1.00 on 6, 0.88 (split line) and 0.60 (duplicated chalkboard run) on 2 | `docs/evidence/phase-5/recall-eval.json` |
| 2026-10-27 | Leader dots: removed in 3/3 menu runs, 12 before/after crops | `docs/evidence/phase-5/leader-dots-before-after.png` |
| 2026-10-27 | Region policy: prices keep Latin numerals, logos/decoration skipped, SFX optional-off | `docs/evidence/phase-5/README.md` |
| 2026-10-27 | Curved/rotated headline: read and translated, set as a straight line — **unsupported**, scoped out | `docs/evidence/phase-5/curved-headline.png` |
| 2026-10-27 | Phase 6 gate: comic/menu edited+exported; SVG vs PNG mean diff 0.12 / 0.55 | docs/evidence/phase-6/gate.json |
| 2026-10-27 | SVG render parity (browser vs server): 0.33-0.55 mean abs diff, <=0.43% pixels >40 | docs/evidence/phase-6/parity.json |
| _pending_ | **Time to localize one page by hand vs. with Naqsh** | Stopwatch protocol below |

### Running API spend (receipt-based)

Recomputed 2026-10-27 19:20 Cairo with `backend/scripts/spend_report.py`:

| Source | Count | Cost |
| --- | --- | --- |
| Pipeline job receipts (`backend/.cache/jobs/*/job.json`) | 77 jobs | **$2.3932** |
| Script-call ledger (`docs/evidence/api-spend.jsonl`) — probe/eval/script calls | 61 calls | **$0.3083** |
| Probe receipts (`backend/.cache/probes/*.json`) | 11 files | **$0.0436** (backfilled, see below) |
| **Traceable total** | | **$2.7451** |

Demo replays are listed separately by `spend_report.py` (13 jobs, $0.3033 of recorded
cost) and are **not** added to the total: that money was already paid by the original
runs.

Probe receipts did not carry a cost field: the Phase 1 scripts stored the response
body/usage but never wrote a cost, so the total used to show $0.00 for them. The
costs are now **backfilled** by `backend/scripts/backfill_probe_costs.py` from the
recorded model, token usage or image count and the published prices (Spark tokens,
$0.01/image, SAM $2.50/1000); each receipt is marked `cost_backfilled: true` with a
`cost_basis` string, so the number is never mistaken for one the API returned. They
are recoverable from the receipts, not lost — but they are recomputed, not observed.

**The earlier discrepancy, resolved:** the Phase 3 report showed $0.5033 while a
receipt-only scan said $0.4657. Both were real: $0.4657 was pipeline jobs only
(6 step-0 + 6 typesetting-gate + 2 live runs), and $0.5033 added the four
fault-injection script calls ($0.0377) that are not jobs. The **correct task total is
$0.5034**; the report should have labelled which side of the line each number sat on.
New script calls now append to the ledger so this cannot drift again.

### Typesetting engine and fonts (why)

Pillow does not shape Arabic, so the Phase 2 renderer used presentation-form fonts
through `arabic-reshaper`. Phase 3 replaces it with **HarfBuzz** (joining, ligatures,
mark placement) plus FreeType rasterising; Western digits are shaped as separate LTR
runs placed right-to-left so `شاي 25` stays in order. Fitting measures the **shaped
ink** (ascenders, descenders, diacritics), not advance widths. Fonts, all SIL OFL with
licences committed: **Tajawal Regular/Bold** (speech, display, chalk), **Noto Naskh**
(print/serif), **Amiri** (calligraphic option). Cairo and Reem Kufi were tested and
rejected for broken substitution in this renderer; Noto Kufi is retired. The style map
is still keyword-based (Spark's `font_style`), not a real matcher.

### Visual self-check (why, and what it does not do)

One Spark vision call over 100%-zoom crops flags overflow, clipping, unreadable text
or a wrong translation; the pipeline makes exactly one fix pass (shrink to 80% for fit,
re-ask the translation for meaning) and re-checks once. On the injected-fault set it
caught **11/12 faults (91.7%)** with **0/6 false positives**, but the issue *class* was
right only **8/12 (66.7%)** — clipping is usually called overflow (same fix, wrong
label) and one clipped case was missed. This is a 12-region injected test from one
page, not a benchmark; the clean runs (0 flags) say nothing about detection.

### UI language toggle

Chrome is English by default with an Arabic switch (persisted, `?lang=ar` for links).
Content stays Arabic: translations render `dir="rtl" lang="ar"` in both UI languages,
and the before/after figures are pinned `dir="ltr"` so the image is never mirrored.
Arabic UI copy is a first draft marked `TODO(native-review)`; the result screen was not
screenshot-tested (needs a live backend) — checklist in `docs/evidence/phase-3/ui-toggle.md`.

### Region strategy and recall (Phase 5)

Ground truth is the generation prompt (or the visible strings of the public-domain
poster). Eight fixtures, one read each: **recall 1.00 on every page**, precision 1.00
on six. The two exceptions are explained, not hidden: the menu returns its six prices
as separate `price` regions (correct behaviour, counted apart from precision), the
public-domain poster's top line is split into two regions, and one chalkboard run
duplicated two item regions (a second run returned three clean regions).

Policy, returned by Spark and logged per region in the receipt: dialogue/caption/
signage/menu_item/title → translate; price → keep Latin numerals; logo/decorative →
skip (original pixels untouched); SFX → optional, off by default. Skipped and
optional regions never enter segmentation or repainting.

Curved/rotated headlines are **unsupported**: the text is read and translated but set
as a straight line in its bounding box, so an arched headline does not follow the arc.
That is scoped out of the hackathon rather than faked.

Leader dots from printed menus are now detected (evenly spaced small ink blobs, gated
on the OCR text containing a dot run) and repainted away: 3 live runs, 12 before/after
crops, no dots left.

### Editor and layered export (Phase 6)

One JSON job document drives the editor and both exporters: page settings (register,
numeral style: Latin default or Arabic-Indic), plate/composite paths, and layers with
type, action (translate / keep numerals / skip), source text, Arabic per register,
box, font, size, per-line baselines, colour, z-order, visibility and lock. The
editor is reachable at `/?job=<id>` after a run.

Export: layered **SVG** (source-pixel viewBox, embedded plate, cover patches, one
`<text>` per line with `direction="rtl"` and `unicode-bidi`, stable layer ids, hidden
original reference), an **outlined** variant with glyphs as paths, a **PNG** at exact
source size, and a **ZIP** with both SVGs, the plate, the exact OFL fonts, their
licences and an install README. Fonts are bundled because SVG text only names a
family: without the font installed the browser substitutes and Arabic breaks, so the
editable SVG alone is not safe to hand to a client.

**Parity:** browser (headless Chrome, fonts via `@font-face`) vs server render of the
same document — mean absolute difference **0.33–0.55** on comic, menu and chalkboard,
≤0.43% of pixels differing by more than 40 (glyph-edge antialiasing). No layout or
shaping differences observed.

**Gate:** on the comic and menu, one line was rewritten, one region retranslated to
MSA, one SFX region skipped, one box nudged and one cover patch added; the exported
SVG contains those exact strings and its headless render differs from the editor PNG
by **0.12** (comic) and **0.55** (menu) mean absolute. Evidence and the manual
Inkscape/Figma checklist: `docs/evidence/phase-6/README.md`.

Friction logged: the SVG grows to 5–7 MB because the plate is embedded (fine for
hand-off, heavy for a repo — the gate SVGs/ZIPs were deleted from evidence and are
regenerated by `backend/scripts/gate_6.py`); CI caught `fonttools` missing from
`requirements.txt` after merge and a hotfix PR (#32) restored green.

### Hardening (Phase 6 follow-up)

- **Repo hygiene:** `.tmp/` is in `.gitignore` and **not tracked** (`git ls-files`
  returns nothing under it), so no files had to be removed. Main CI was green before
  and after.
- **Dedupe on real data:** chalkboard read 5×, public-domain poster 3× (read-only, no
  segmentation). Counts before→after: chalkboard 5→5, 3→3, 3→3, 5→5, 3→3; PD poster
  8→8 every time. **No duplicates reproduced**, so the synthetic tests are the only
  evidence that the drop rule fires. Two chalkboard runs returned the item + price as
  two regions; that is the policy working (prices stay separate), not a duplicate.
  Cost: $0.0654 (`docs/evidence/phase-6/dedupe-real.json`).
- **Text-only parity:** diffs restricted to the union of text boxes — comic 3.13 mean
  / 2.57% over 40, menu 4.20 / 3.28%, chalkboard 2.39 / 1.73%. The "SVG render" is
  **headless Chrome (Blink + HarfBuzz)**, not resvg or cairosvg; Chrome shapes Arabic
  natively, which is why the whole-page diff is 0.1–0.5 and the text-only diff stays
  at glyph edges. Diff crops saved for review.

![Text-only diff, comic](evidence/phase-6/textparity-6a8aa7a0829b-diff-crop.png)

- **Editor click-through (Playwright, real mouse/keyboard):** 10/10 — select from the
  list, type in the textarea, reload persistence, drag, resize, undo, redo, cover
  drag, cover persistence, no console errors. Screenshots `e2e-*.png`, results
  `e2e.json`. Fixes found by the click-through and kept: the selection outline now
  takes pointer events (unfilled SVG rects do not), layout results no longer add a
  history entry, a drag produces exactly one undo step, undo/redo PATCH immediately
  (a pending debounce used to restore the pre-undo box), and the editor's layout call
  now sends the current text/box so a debounce can never clobber an edit.
- **Process deviation, stated:** hardening was driven on one branch with one PR, and
  the previous phase's PR #33 was squash-merged (against the repo's "never squash"
  rule) because its commit message was malformed. No history rewrite; this note is
  the correction.

### Demo mode for recording

Five real, already-paid runs are cached under `fixtures/demo/` (comic, menu,
chalkboard, SFX comic, the failing kraft label) with the original receipt: the
recorded stage milliseconds and cost are never altered. `DEMO_MODE=1` hashes the
upload and replays a byte-for-byte fixture match; anything else goes live. The UI
shows an amber **“Demo mode: replaying recorded run”** badge on the result page and
in the editor, and `?clean=1` hides only dev chrome, never the badge. Stage progress
is replayed at the recorded pace (comic 48.3 s, menu 95.6 s — recorded before the
Phase 8 speed work, which is why live runs are now faster than the replay), and re-translate
replays the cached Egyptian/MSA line at cost $0. The cache holds two registers: the
21 MSA lines were paid for once ($0.0270) so the register switch is not a live call.

Honest-use rule, in the README: the final video must include at least one live run.
Recording checklist: `docs/recording-guide.md`.

Verified: demo replay returns the cached regions and the recorded totals; unknown
bytes take the live path (stubbed in the test, so CI spends nothing); the Playwright
demo run is 6/6 (badge, clean, replay visible, receipt, editor badge) and the menu
click-through is 6/6 (select, edit, drag, undo, reload). Playwright is evidence, not
a CI check — it needs a local Chrome.

### Phase 7 — live measurement and audit

Six live runs with `DEMO_MODE=0` (2026-10-27), receipts in
`docs/evidence/phase-7/live-runs.json`:

| Page | Total median (range) | Cost median (range) | Notes |
|---|---|---|---|
| comic | **54.5 s** (53.1–57.2) | **$0.0263** (0.0254–0.0286) | 3 regions, stable |
| menu | **181.1 s** (162.1–206.8) | **$0.0502** (0.0442–0.0676) | 16 regions (item+price split), one 40.9 s retry |

Wall time was measured for one run per page (57.6 s comic, 189.0 s menu); the rest are
receipt totals, not wall-clock estimates. These Phase 7 numbers are **pre-optimisation**:
the menu's live behaviour then differed from the cached demo run — 16 regions instead of
10, 181 s instead of 96 s, `register_composite` 75.7 s median — and one run needed a
retry. After the Phase 8 work the same page is **61.8 s median (61.5–78.5, n=5)** with
`register_composite` at **1.8 s** (`docs/evidence/phase-8/variance-summary.json`). No run
errored, hung, or failed; 6/6 returned 200. The spend also
includes a few extra live runs produced while a background measurement script was
misbehaving (killed); they are counted, the table uses the six clean receipts.

The time-saved ratio is **removed** (owner decision, 2026-10-29): the owner is not an
editor, so a manual baseline would not be honest. Naqsh's own times remain in the receipts
as context; the only allowed wording is **"faster"**, never a multiplier or minutes saved.

**Audit** (`docs/audit.md`): no key material in the tree or history (`.env` never
committed; the only `LLM_` strings are documentation and a test asserting the key never
leaves the server); Vectr appears only in policy docs; `ASSETS.md` was missing the five
demo-cache directories (25 files) and now reports 0 uncovered of 49 tracked asset files;
README layout gained `docs/evidence/` and `fixtures/demo/`; repo weight is 101.1 MB.

### Menu speed (Phase 8a)

The menu's 181 s median was dominated by Pillow rank filters, not by the models.
Profile on the stored menu job (`docs/evidence/phase-8/profile.json`): alignment ring
39.2 s, per-region coverage 8.7 s, per-mask composite 5.0 s, flat fill 2.5 s; phase
correlation itself was 0.36 s.

Replacing Pillow `MaxFilter`/`MinFilter` with `cv2.dilate`/`erode`, unioning the masks
before one dilation instead of one per mask, and running **segment and clean_plate
concurrently** (independent HTTP calls on the same bytes) cut the register+coverage
work from **56.3 s to 3.7 s** and the menu end-to-end median from **181.1 s to 61.6 s**
(two live runs: 61.5 s and 61.8 s; 16 regions both, cost $0.0499/$0.0520, unchanged).
Equivalence on three stored jobs: **composite max pixel diff 0, 0 differing pixels**;
coverage masks identical too (`docs/evidence/phase-8/morph-equivalence.json`).

Because stages now overlap, `total_ms` is wall time and `stage_ms_sum` keeps the sum;
without that change the receipt would have overstated the elapsed time (it did on the
first post-change runs: 122 s total against 98.9 s wall).

### Variance after the speed work (Phase 8b)

Every post-change live run, same code, `DEMO_MODE=0`:

| Page | Runs | Wall median (range) | Cost median (range) | Regions |
|---|---|---|---|---|
| comic | 3 | **33.8 s** (28.5–37.4) | $0.0262 (0.0257–0.0291) | 3 |
| menu | 5 | **61.8 s** (61.5–78.5) | $0.0520 (0.0367–0.0661) | 16 |

The menu count includes the two earlier post-change runs; a previous pair on the same
code took **89–122 s**, which is not in the JSON because it was not saved at the time —
stated here rather than dropped. `register_composite` is now 1.0–1.8 s median for both
pages (it was 75.7 s on the menu before the speed work). Evidence:
`docs/evidence/phase-8/variance.json` and `variance-summary.json`. The manual baseline
is still empty; no ratio is claimed.

### UI theme pass — why it came after Group 1

Group 1 fixed behaviour but **did not change the palette**: `frontend/src/index.css`
still defined the original light `@theme` (`--color-paper: #f6f1e7`, `--color-sand:
#e7dcc8`, serif `--font-arabic`), so every existing `bg-paper` / `text-ink` utility
kept rendering beige. The design brief was written but not implemented.

This pass implements it: dark tokens (`bg #0E0F12`, panel `#16181D`, raised `#1D2026`,
border `#2A2E36`, text `#E6E8EE`, muted `#9AA1AD`), indigo accent **#5B6CFF**, red only
for destructive/error, and legacy class names remapped to the dark palette so nothing
silently kept the old colours. **Inter** and **IBM Plex Sans Arabic** are bundled from
google/fonts (OFL, served by `/api/fonts`, no CDN) and used for UI chrome and Arabic
samples. Lucide icons replace the undo/redo/Original text controls; all-caps letter-spaced
labels and the brand-red selection outline were removed (selection is now accent).
Export buttons remain text until Group 2, as instructed.

Verified: body background `rgb(14,15,18)`, text `rgb(230,232,238)`, Inter resolved,
fonts served 200; screenshots at 1440×900 in `L:\naqsh-review\theme\`
(`editor-1440.png`, `home-1440.png`, `theme.json`); click-throughs still green
(comic 10/10, menu 6/6, Group 1 8/8).

### UI Group 1 — functional fixes from the owner click-through

- Font dropdown now re-typesets through the HarfBuzz fitter (the old handler called the
  layout before the font change reached the document). Options carry Arabic samples.
- Size is live: slider + number (1–1000), capped so text stays in its box, plus **Fit to
  box**. Changing digits re-lays out the page and reloads the canvas.
- Re-translate has a busy state, error, cost, and is undoable. The server locks per
  region and allows 6 calls per job per minute (`throttle.py`), so double-clicks cannot
  bill twice.
- **Reset to AI result** restores the first generation snapshotted at document creation
  (text, font, size, colour, box, action), not a document reload; undoable.
- **Original** hides every overlay and layer while on.
- Before/after slider rebuilt: container is LTR, reveal is clip-path based, the original
  sits above all overlays, divider is draggable, and the range input is keyboard
  operable.
- "Register" renamed **Arabic style** with help text; the old "Translate" toggle is now
  **Localize region** (off keeps the original artwork). Re-translate is the only action
  that costs money.
- **Digits** labelled `0123 / ٠١٢٣` with helper text and a live sample.

Checks: `pytest -q` 70 passed; `typecheck` clean; Group 1 Playwright 8/8
(font, live size, reset, original, slider keyboard + pointer, digits, console), existing
comic 10/10 and menu 6/6 still green. Screenshots outside the repo at
`L:\naqsh-review\group1\`.

### UI Group 2 — layers, tools, export

- Layers panel lists every layer: original reference and clean plate (locked rows) plus covers and text regions, sorted by z; inline rename, eye/lock, up/down and drag reorder, selection sync with the canvas.
- Cover tool in the left toolbar (Select, Text, Cover, Eyedropper) with rectangle or ellipse patches; fill via the shared colour control; move/resize through the normal selection box; eyedropper samples the composite and applies to the selected layer.
- Shared colour control: native picker, typed hex, recent colours, eyedropper (used by text colour and patch fill).
- One Export dropdown with Layered SVG, Outlined SVG, PNG and Bundle (ZIP), each with a one-line description; a preparing/exported toast replaces the four link buttons.
- Cover shape is persisted (shape) and honoured by the canvas, the layered SVG (ellipse element) and the PNG render.

Checks: pytest 72 passed; Group 2 Playwright 7/7; comic 10/10; menu 6/6; Group 1 12/12; axe contrast 0. Screenshots at \L:\\naqsh-review\\group2\\\.

### Group 3 polish follow-up

- Home now uses the same wording as the editor: **Arabic style** with full option labels and a one-line helper.
- Removed the duplicated digits sample in the top bar; the select itself shows 0123 / ٠١٢٣.
- Review screenshots are now clean: home with ?clean=1, editor on the menu job (no leftover test covers).
- Region naming run again on the menu (its document had been reset by tests): .0042; naming ledger total across all runs .0092 for three calls.
- Known risk: the Group 2 click-through deletes a job document to reset state, which also deletes cached region names; comic names were wiped by that test after the naming run.

Checks: 72 backend tests, comic 10/10, menu 6/6, Group 1 12/12, Group 2 8/8, axe contrast 0.

### Background split into layers

- New: the cleaned background is no longer one locked composite. A **Scenery** layer holds the page with speech-bubble areas cut out, and each **Bubble** is its own layer, cut from the cleaned plate.
- Bubbles come from one SAM 3.1 concept call per page (`speech bubble`); regions with no SAM bubble use their reading box as a rectangular fallback. Pages with no dialogue/caption regions (the menu) get a scenery layer only, with no fake bubble rows.
- Editor: scene + bubble layers appear in the Layers panel, toggleable, renameable, reorderable; hiding a bubble reveals the scenery hole.
- Export: the layered SVG has `Scenery` and `Speech bubbles` groups and omits hidden layers; the PNG composites scene + visible bubbles + covers + text on a white page.
- Assets and `background.json` live in the job folder, so the layers survive a document rebuild/reset (verified by the editor and menu click-throughs).
- Limits: SAM found 2 of 3 bubbles on the comic (the title used the box fallback); the menu has no bubble detection; this is a per-job build script, not yet part of `run_page_job`, and the demo cache documents are not rebuilt with background layers.
- Evidence: `docs/evidence/ui/background-layers.json`; screenshots at `L:\naqsh-review\bg\01-layers.png`, `02-bubble-hidden.png`, `03-bubble-restored.png`.

### Background build inside the pipeline + rebuilt demo comic/menu

- `run_page_job` now builds the background layers itself: one SAM 3.1 `speech bubble` call, `scene.png` with bubble holes, `bubble-<region>.png` assets, and `background.json` with each bubble's **source** (`sam` or `box_fallback`) and the counts.
- The stage is recorded as `background` with `bubbles`, `sam`, `box_fallback`; the counts are also written to the server log. A failure is caught, logged as a warning, recorded on the stage, and the job continues with the single plate (verified by two live runs that failed on a BBox bug and still finished).
- Rebuilt through the real upload path (POST `/api/localize`, live mode): comic `4e251c89edaa` (39.5 s, $0.027963, bubbles 3 / sam 2 / fallback 1) and menu `2c34e573a187` (75.9 s, $0.051303, bubbles 2 / sam 0 / fallback 2).
- Layers now: comic **scene, bubble-t1, bubble-t2, bubble-t3, t1, t2, t3**; menu **scene, bubble-t2, bubble-t16, t1..t16**.
- Demo cache rebuilt from those live jobs: `fixtures/demo/comic` and `fixtures/demo/menu` now carry `background.zip` (scene + bubbles + manifest); replay on a demo-mode server returns the same layer list. Total cache 14.21 MB (was 11.0 MB). The chalkboard, sfx and label demo entries were **not** rebuilt and have no background layers.
- Limits to eyeball: the menu's two bubbles are both **box_fallback** (SAM found no bubble), so they may be false positives around dialogue-typed regions; the comic's title banner is also a box fallback. Only comic/menu demo entries were rebuilt.
- Evidence: `docs/evidence/ui/pipeline-background.json`; screenshots not regenerated in this step.

### Background suppression + all five demo entries rebuilt

- `build_assets` now suppresses **all** bubble layers when SAM returns zero bubble objects, even if regions are typed dialogue/caption. The background stage records `fallback_suppressed: true`; per-region `box_fallback` still applies when SAM returns at least one object.
- Menu live run (`9b6f89fbc2b3`, 90.3 s, $0.0391): **0 bubbles, 0 sam, 0 fallback, suppressed true** — scenery only, no more holes around non-bubble text.
- SFX page (`8e07fe0a4a4d`, 32.3 s, $0.0276): 0 bubbles, suppressed true. Chalkboard (`231bfa7361a0`, 69.8 s, $0.0445) and label (`76bb774d72f1`, 71.0 s, $0.0422): 0 bubbles, suppression false (no dialogue/caption candidates, SAM not called).
- Comic (`4e251c89edaa`) stays 3 bubbles: **2 sam, 1 box_fallback**; it predates the suppression flag, so its stage has no `fallback_suppressed` field.
- All five demo entries rebuilt from these real receipts: **comic, menu, chalkboard, sfx-comic, label-fail**; cache is now **20.02 MB**. Demo replay of each returns the same layer lists (comic: scene + 3 bubbles + 3 text; the other four: scene + text only).
- README "What's new" gained one line about the layered background.
- Limits: the suppression change is one rule (zero SAM objects); quality of box_fallback on pages with >=1 detected bubble is still unverified visually; comic's flag is absent because it was not re-run.

### Background follow-ups: dialogue-only fallback, explicit live mode, rebuilt demos

- Bubble layers are now **dialogue only**. SAM zero objects still means scenery only (menu); with SAM output, `box_fallback` is only allowed for dialogue regions — captions, menu items, prices and signage never become bubbles.
- `LIVE_MODE=1` is required for any paid call. `/api/localize` (unknown uploads) and `/api/retranslate` return 403 otherwise; demo replay still needs no key. Startup prints `=== Naqsh LIVE MODE — paid model calls ENABLED ===` or the DEMO equivalent.
- Observed in a real server log: comic `7e997e7b7e9f` → `background bubbles=2 sam=2 box_fallback=0`; chalkboard `79753c06d42e`, sfx `3d06d47ba521`, label `f6d1bc33524b` → 0 bubbles, 0 fallbacks.
- Rebuilt demos after the rule change (live, cap noted): comic `7e997e7b7e9f` $0.0298, chalkboard `79753c06d42e` $0.0392, sfx `3d06d47ba521` $0.0258, label `f6d1bc33524b` $0.0269 → **$0.1216** total (the three requested entries were $0.0919 of it; comic was re-run because the caption rule removed one bubble). Menu was not re-run: its layers (scene + 16 text) do not change under the rule.
- Demo cache rebuilt from the new receipts: **20.40 MB**, +0.38 MB. Demo replay layer lists verified for all five entries (comic: scene + bubble-t2 + bubble-t3 + 3 text; menu/chalkboard/sfx/label: scene + text only).
- Editor/export: scene, bubble and text layers share the Layers panel (name, eye, lock, drag reorder); locked layers cannot be drag-reordered. The ZIP now carries `layers.json` (id, kind, name, box, asset, z, locked) plus `layers/` with the scene and bubble PNGs, matching the SVG's Scenery / Speech bubbles / Cover patches / Text groups and the PNG composite.
- Evidence: `docs/evidence/ui/background-followups.json`.

### Background-layer switch

- The home upload now has a **Background layers** switch (default on). On = current behaviour: scenery + speech-bubble layers (one SAM pass and asset generation). Off = skip the background stage entirely; the job only translates and produces text layers, so the page keeps the flat composite.
- API: `POST /api/localize` accepts `background_layers=true|false`; the receipt records `background: {enabled: false, skipped: "disabled by request"}` when off.
- This was added because the background pass visibly increased processing time; no speed claim is recorded until timed with the switch off vs on.

### English test suite + demo candidates (2026-10-31)

- 13-page English suite (10 code-drawn text over Muse Image art, 3 model-rendered-text
  expected-fail pages) + 40 translation strings in both registers. Details and run
  commands: `docs/test-suite.md`.
- Live eval (13 pages, background layers on): cost **$0.4296**, **2.3–97.5 s/page**,
  **$0.0049–$0.0445/page**, recall **0.71–1.00** on pass pages (mean 0.97), CER
  **0.0–0.794**; comic 3 bubbles = 3 bubble layers; no-text page = 0 regions.
- Translation: 40/40 in both registers; Arabic ratio 0.968–1.0 (Egyptian) / 1.0 (MSA);
  digits preserved 38/40 Egyptian, 37/40 MSA; review sheet at
  `L:\naqsh-review\arabic-review\review.md`. No correctness claim.
- Five demo candidates, one live run each: **45.2–93.6 s**, **$0.0251–$0.0459**;
  contact sheet at `L:\naqsh-review\demo-candidates\contact-sheet.jpg`.
- Task spend: **$0.8184** of the $1.00 cap (images $0.18 + live runs $0.6279 +
  translation $0.0105).

### Time-saved claim — removed

Owner decision, 2026-10-29: **no time-saved ratio is claimed**. The owner is not an
editor, so a manual baseline would not be honest. The Naqsh medians below stay as context
for the receipts; the only allowed comparative wording is **"faster"**.

| Page | Regions | Naqsh median (live receipt) |
|---|---|---|
| comic `01-comic-flat.png` | 3 | 33.8 s (0.56 min) |
| menu `03-menu-paper.png` | 16 | 61.8 s (1.03 min) |

Source: `docs/evidence/phase-8/variance-summary.json`. No manual column, no ratio.

## Media worth using (screenshots / clips)

Collect as we go; each entry says what it proves.

**Build-in-public clips:** save a short before/after clip as each feature lands. The
pipeline already writes `before-after.png` per job, and the editor can export the
current page; keep clips next to the evidence they belong to. Posting anytime during
the event is allowed and build-in-public posts do not affect Most Viral eligibility
(organizer answer, 2026-10-27).

| Date | File | Shows |
| --- | --- | --- |
| 2026-10-27 | `assets/generated/test-panel.png` | The generated, rights-clean test page (before) |
| 2026-10-27 | `assets/generated/test-panel-speech-bubble-masks.png` | SAM 3.1 masks landing exactly on both speech bubbles |
| 2026-10-27 | `assets/generated/test-panel-caption-masks.png` | A box prompt turning Spark's bbox into a precise caption mask |
| 2026-10-27 | `assets/generated/test-panel-cleaned.png` | Lettering erased, artwork intact (the clean plate) |
| 2026-10-27 | `assets/generated/test-panel-before-after.png` | The before/after pair — strong X-post candidate |
| 2026-10-27 | `docs/evidence/phase-2/before-after-egyptian.png` | Phase 2 end-to-end: generated page → Arabic page |
| 2026-10-27 | `docs/evidence/phase-2/masks-overlay.png` | SAM masks over the page: what became editable layers |
| 2026-10-27 | `docs/evidence/phase-2/clean-plate-composite.png` | The plate after registration and masked compositing |
| 2026-10-27 | `docs/evidence/phase-2/failure-ghost-lettering.png` | The honest failure: an edit that left ghost lettering |
| _pending_ | editor | A region being fixed in the layer editor |
| _pending_ | export | SVG layers opened somewhere that proves they are editable |

## Demo video outline (3 minutes)

1. **0:00–0:20 — Problem.** Arabic creators localize by hand; RTL tools break.
   Show a real before (rights-cleared) and say the claim: *X minutes by hand vs.
   Y with Naqsh*.
2. **0:20–1:30 — Pipeline.** Upload → SAM masks appear → Spark reads and
   translates → plate repainted → Arabic typeset RTL. Narration names the model
   doing each step.
3. **1:30–2:20 — The editor.** Fix a region: change text, drag position, switch
   font, resize; show it fitting the bubble.
4. **2:20–2:50 — Export.** Layered SVG + PNG; open the SVG and show selectable
   text layers.
5. **2:50–3:00 — Who it's for / close.** One sentence on audience and the
   measured time saved.

Rules: only what was built during the hackathon; no third-party copyrighted
pages; captions for the Arabic; record at 1080p; upload unlisted to YouTube.

## Submission checklist (Phase 9 owns this)

- [ ] Repo public, no secrets in history (`git log -p` scan + GitHub secret scan)
- [ ] README "What's new" section accurate
- [ ] ASSETS.md complete, every asset licensed
- [ ] Demo video unlisted, link opens in a private window, ≤ 3:00
- [ ] Form fields filled, description proofread, X post linked (optional track)
- [ ] Submitted on 3 Nov (buffer before 4 Nov 21:00 ET)
- [ ] Submission confirmation screenshot saved in `docs/`

## Rules relayed by the owner (screenshot pending)

Relayed from Cerebral Valley by the owner on 2026-10-28. **Marked relayed, screenshot
pending** until the owner saves the evidence in L:\\naqsh-review\\rules-evidence\\.

- The video must **demo the product that was built**, not slides.
- It should run **3:00** and be **understandable in English**.
- An editor who does not touch the build **does not need to be a participant**.

These are recorded, not yet confirmed by screenshot; no submission decision depends on them
until the owner confirms.

## Organizer answers (verbatim)

### Discord #questions — 2026-10-31

- **Live URL:** "A public live URL is not required. Judges need a project that runs from
  the public repo's setup instructions, plus the 3-minute demo video. A hosted version is
  optional, so you can deploy it, but judging doesn't depend on it."
- **Video:** "The demo video should show the working product with the live Meta model
  calls visible, and judges can test with their own keys if needed. Recorded sample runs
  are only a fallback, so if your public deployment runs in demo mode, make sure the repo
  still runs live from its setup instructions and the README explains how to use the demo
  mode."

**PENDING — no answer yet, do not assume:** whether outside AI coding tools (DeepSeek,
Claude) are allowed. (The owner will paste the exact text when available.)

### Discord #questions — 2026-10-28 21:49 Cairo

- Muse Image is an allowed model, so demo artwork generated with it may be used in the
  video and repo. The rules only exclude assets I don't have rights to. No on-screen
  credit is required. Describing the Muse Image use in the "use of Meta products" field
  is enough.
- The video link only needs to be accessible. Unlisted YouTube is fine. The repo must be
  public.
- The submission can be edited at the submit URL until the deadline. No edits are allowed
  after it.
- Most Viral counts only likes, reposts and comments on the X post linked in the
  submission, through Nov 8 EOD. No hashtag is required. Posting anytime during the event
  is allowed. The Community Vote is separate.

### Discord #questions — 2026-10-27

1. **Demo video link:** any accessible link that lets judges watch works (unlisted YouTube is fine).
2. **Submissions can be edited until the deadline**, so the X post link can be added later.
3. **Most Viral is separate from the Community Vote**: highest total likes + reposts + comments on the X post linked in the submission, counted through Nov 8 EOD. Posting anytime during the event is allowed, and build-in-public posts don't affect eligibility.
4. **Community Vote is on the public gallery**, one vote per verified account, winner announced Nov 16.

