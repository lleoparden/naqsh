# Plan: Naqsh — hackathon build through 3 November

**Method:** ECC `/plan` workflow (restate requirements → surface risks → phase the
work → wait for confirmation), taken from the ECC plugin's own command definition
at `C:\Users\mosta\.claude\plugins\cache\ecc\ecc\2.2.3\commands\plan.md`. The ECC
skill was not invocable by name in this session; the owner confirmed on 2026-10-27
to use that workflow and record the source here.

**Source requirements:** the owner's Phase 1 brief (sections 1–7) and the findings
in [`api-findings.md`](api-findings.md).
**Complexity:** Large.
**Status:** Phase 1 executing. **Phases 2–10 need owner approval before work
starts.**

## Summary

Naqsh takes one image (comic page, poster, menu) and returns editable, layered
Arabic. The build is planned backwards from the two artifacts judges score: a
working demo and a three-minute video. So the pipeline is assembled end to end on
one page early (Phase 2), the four risky stages are hardened behind measurable
gates (Phases 3–5), the layer editor and export follow (Phase 6), and the last two
phases are measurement, video, and the submission package itself (Phases 9–10).

## Requirements restatement

- **Product:** upload → SAM 3.1 segmentation → Muse Spark read + translate +
  style → Muse Image repaint → Arabic RTL re-typeset and fitted → layer editor →
  layered SVG + PNG.
- **Audience:** Arabic webcomic creators, small publishers, small businesses.
- **Measurable claim:** time to localize one page by hand vs. with Naqsh, with a
  written protocol and recorded numbers.
- **Meta tooling story:** several models cooperating, each doing something another
  tool could not; documented with observed behaviour.
- **Hard constraints:** new work only, public repo, no secrets, rights-cleared
  assets only, clear commit history.
- **Deadline:** submit 3 Nov (hard deadline 4 Nov 21:00 ET = 5 Nov 04:00 Cairo).
  Backup demo video 30 Oct. Feature freeze 1 Nov.

## Patterns to mirror

| Category | Source | Pattern |
| --- | --- | --- |
| Branching | Vectr history (read-only) | `feat/`, `fix/`, `docs/`, `chore/` + lowercase slug; one branch per work item |
| Commits | Vectr history | Conventional Commits, scope + imperative summary, body states what/why/verified/limits |
| Issues | Vectr `.agents/workflows/issue-ready.md` (re-created) | One epic per phase, one sub-issue per approved slice, PR closes the issue |
| Evidence | Vectr `verify:artifact` habit (idea only, new code) | Every gate writes a receipt/JSON/PNG under `backend/.cache/probes/` or `docs/evidence/` |
| Docs duties | This repo `AGENTS.md` | findings + submission notes updated in the same PR as the behaviour |

## Program at a glance

| Phase | Dates (Cairo) | Goal | Gate (go/no-go) | If the gate fails |
| --- | --- | --- | --- | --- |
| **1. Setup + probes** | 27 Oct | Repo, workflow, one probe per model | All three models answer; SAM masks decode; Image edit returns an image | Escalate to owner; fall back per findings |
| **2. Vertical slice** | 27–28 Oct | One page through the whole pipeline, rough UI | Before/after page exists; cost and wall time measured | Cut stages to reach a visible before/after (cover instead of inpaint) |
| **3. RTL typesetting + fitting** | 28–29 Oct | Arabic set properly and fitted per region | 5/5 regions fit with no clipped diacritics/ascenders at 100% zoom; ≤2 manual fixes per page | HarfBuzz shaping + per-region auto-shrink; then editor-first fallback |
| **4. Clean plate quality** | 29–30 Oct | No ghost lettering | 4/5 regions clean at 100%; artwork outside masks unchanged | Classical inpaint (B), then opaque cover (C) |
| **5. Region strategy** | 29–30 Oct | Reliable text regions across page types | ≥80% of text regions found on 5 pages | Hybrid: Spark bboxes → SAM box/point prompts; plus manual add-region |
| **6. Layer editor + export** | 29–31 Oct | The centerpiece UI and true layered export | Edit text/pos/font/size; SVG has selectable `<text>`; PNG matches | Ship SVG groups + flat PNG; drop per-glyph fanciness |
| **7. Measurement + backup video** | 30 Oct | The Impact number and a safety-net recording | Hand-vs-Naqsh numbers recorded; backup video file exists | Record later; number with n=1 and say so |
| **8. Polish** | 31 Oct | Second page type, errors, cost table | Menu page works; failures are graceful; cost/page recorded | Narrow the demo to the comic page |
| **9. Freeze + final video** | 1–2 Nov | Lock features, record the 3-minute video | Video ≤3:00, unlisted, link opens privately, shows export | Re-record from the backup outline |
| **10. Submission** | 3 Nov | Everything section 7 produced, checked, submitted | Form submitted + confirmation screenshot | Submit the best available; 4 Nov is the cliff |

Dependency order: 1 → 2 → (3, 4, 5 in parallel where possible) → 6 → 7 → 8 → 9 → 10.
Phase 3 is the riskiest and starts the day the slice runs.

---

## Phase 1 — Setup and API smoke tests *(executing now)*

**Deliverables:** repo scaffold and structure; agent instruction files re-created
for Naqsh; public GitHub repo with an early, honest commit history; one probe per
model (`smoke_spark_text`, `smoke_spark_image`, `smoke_sam`,
`smoke_image_generate`, `smoke_image_edit`); `docs/api-findings.md`;
`docs/submission-notes.md` seeded; this plan.

**Gate:** each model answers with the documented shape; SAM's mask payload decodes
to `H×W` bits; the Image edit returns a usable image; latency and cost recorded per
call. **Exit evidence:** receipts in `backend/.cache/probes/` + the findings table
filled in with measured numbers.

**Result (2026-10-27, gate met):** Spark text 2.0 s / $0.00131 with valid Arabic
JSON; Spark vision 6.8 s / $0.00606 reading 3/3 regions; SAM 3.4 s / $0.0025 for two
bubble masks at 0.961; SAM box prompt refined a caption to a 93%-fill mask; Muse
Image generate 12.2 s / $0.01; Muse Image edit 13.6 s / $0.01 with all lettering
removed and a ≈16 px page shift that must be registered. That probe spent ≈25 s of
model time. Current per-page cost, from live receipts: comic (3 regions)
**$0.0257–$0.0291**, menu (16 regions) **$0.0367–$0.0661**
(`docs/evidence/phase-8/variance-summary.json`). Details in [`api-findings.md`](api-findings.md).

**Non-goals:** no pipeline code, no editor, no prompt tuning beyond the probe.

## Phase 2 — Vertical slice on one page *(done 2026-10-27)*

**Goal:** the ugliest possible end-to-end run that a judge could still watch:
upload the generated test panel → regions → Arabic → repainted plate → re-typeset →
download.

**Slices:** `backend/app/pipeline/` stage functions with a `PageJob` state object;
one endpoint `POST /api/jobs` + `GET /api/jobs/{id}` (polling is fine); a frontend
screen that shows stages as they complete; a `docs/evidence/` before/after pair.

**Gate:** one page completes; total cost ≤ $0.10 and wall time recorded; before and
after images are visually checked by the owner. **Fallback:** replace the clean
plate with the opaque-cover technique so the Arabic is readable, and continue.

**Result (2026-10-27, gate met):** `POST /api/localize` runs read → segment →
clean plate → register/composite → typeset → render on the generated panel in
**25–30 s**, **$0.0184–$0.0194** per page, with a per-stage receipt. Arabic is set
right-to-left inside the bubble/panel the region came from, in the original ink
colour. Register switch (Egyptian / MSA) changes the translations and nothing else.
Evidence: `docs/evidence/phase-2/`.

**Open issue carried into Phase 4 (the reason that gate exists):** the Muse Image
edit is intermittent. In 7 runs, 2 left a visible ghost ("MORNING" in the right
bubble) and 1 smeared the caption panel. The masked composite is correct — the
ghost is *in the plate*. `dirty_ratio` correlates (clean ≈0.05, ghosted ≈0.08–0.13)
but overlaps, so it is recorded, not acted on. Phase 4's gate must make this
deterministic.

## Phase 3 — RTL typesetting and fitting *(riskiest)*

Why early: Arabic shaping, bidi, and bubble fitting are where a localization tool
lives or dies, and where the most unknowns are.

**Work:** font choice (open-licensed Arabic faces; record in `ASSETS.md`);
shaping via HarfBuzz (`uharfbuzz`) rather than trusting the browser; per-region
layout with line breaking that respects the bubble polygon from SAM; auto-fit that
tries sizes, then leading, then a minimal rephrase request back to Spark; diacritic
and ascender clearance; RTL punctuation and mirrored brackets.

**Gate:** on 5 regions across 2 pages — no clipped diacritics or ascenders at 100%
zoom, text inside the bubble polygon, ≤2 manual fixes per page. **Fallback order:**
(a) tighter auto-fit with a tolerance envelope; (b) Spark asked for a shorter
variant with an explicit character budget; (c) ship editor-first: place text with
visible fit guides and let the user size it, documenting the limit honestly.

## Phase 4 — Clean plate quality *(in progress 2026-10-27)*

**Work:** Plan A composite (edit the page, keep only masked pixels); masking edge
feather; Plan B classical inpaint (OpenCV Telea/NS) seeded with sampled fill;
Plan C opaque vector cover; a side-by-side receipt image per page.

**Gate:** 4/5 text regions show no ghost lettering at 100% zoom, and pixels outside
masks are unchanged (hash check). **Fallback:** move to Plan B, then Plan C, and
record which plan each page used in the demo notes.

**Implemented (2026-10-27):**

- **Diagnosis first.** On three saved failing runs, residual lettering was mostly
  *outside* the repaint coverage (e.g. 6,894 px outside vs 5,444 inside), because
  the original lettering was taller than both Spark's reading box and the SAM
  mask. The plate itself was clean. Fix: coverage is grown from the source's real
  ink extent (`coverage.py`), not from the guessed box.
- **Registration metrics.** The receipt now reports a ring residual (8–24 px
  outside each mask) per region, whether the offset is vertical-only, and the
  source/plate scale ratio. `outside_untouched_mean_diff` is kept but labelled
  tautological.
- **Detector.** Muse Spark vision over 100%-zoom region crops (one montage call
  per check) returns `{id, residual, note}` per region. No pixel threshold.
- **Routing.** Muse plate → check → one retry → flat-interior fill for flat
  regions → Telea inpaint for textured ones; every region records its strategy.
- **Gate assets.** Five rights-clean pages with different backgrounds (flat comic,
  watercolour poster, printed menu, chalkboard, kraft label), two runs each.

**Gate result (2026-10-27): FAILS the 9/10 bar.** Detector says 7/10 runs are free
of text residual, but the plate flattens painted texture on the poster (2/2) and
leaves faint ghosts plus a flat painted patch on the photographed label (2/2).
Comic, menu and chalkboard are usable (5–6/10 by eye). Cost $0.2975 for ten runs,
$0.0298/run, 75 s/run. Full analysis and evidence: `docs/evidence/phase-4/`.
**Fallback taken:** the demo is scoped to stylised pages; textured backgrounds stay
a documented limit, with thin-stroke inpainting and a manual cover tool as the
Phase 5/6 follow-ups.

## Phase 5 — Region strategy

**Work:** decide how text regions are found per page type: SAM concept prompts
(`"text"`, `"speech bubble"`, `"caption box"`), Spark bbox proposals used as SAM
box prompts, and manual add/remove in the editor. Cache by content hash.

**Gate:** ≥80% recall of human-marked text regions on 5 pages, with precision
reported (false regions are editor deletions, not fatal). **Fallback:** Spark
proposals + SAM point prompts; if both are weak, default to manual region marking
for the demo and state it as a known limit.

## Phase 6 — Layer editor and export

**Work:** the canvas editor: region list, per-region text/position/font/size,
RTL-aware text box, fit guides, undo; export to SVG with real `<text>` layers +
embedded/served fonts, and a flat PNG at source resolution.

**Gate:** a judge can change text, drag a region, switch font and size, then export;
the SVG opens in a browser and Inkscape with selectable text; PNG matches the
editor. **Fallback:** SVG with grouped text + documented font requirement if
embedding proves unreliable.

## Phase 7 — Impact measurement and backup video

**Work:** run the stopwatch protocol in `submission-notes.md` (hand baseline vs.
Naqsh, same page, same definition of done); record the numbers; record a rough
screen capture of the whole flow as the backup demo.

**Gate:** numbers recorded with method and sample size; a backup video file exists
by 30 Oct. **Fallback:** reduce to n=1 and say so; the point is a defensible
measurement, not a study.

## Phase 8 — Polish and the second page type

**Work:** a menu page (different aspect, dense text), error states (no text found,
API failure, safety refusal), cost/latency table per page, first-run onboarding
copy, honest empty states.

**Gate:** menu page completes; each failure path shows a useful message; the cost
table has measured numbers. **Fallback:** demo one page type and say it.

## Phase 9 — Feature freeze, gallery copy and final video

**Work:** freeze on 1 Nov; **write the public-gallery title, tagline and description
(for a public audience, not the judges' technical rubric) and make a thumbnail**
(1280×720 or the gallery's required size, no unlicensed art); script per
`submission-notes.md`; record at 1080p with captions; upload unlisted; verify the link
in a private window; trim to ≤3:00. Save build-in-public before/after clips as they are
made (the pipeline already writes `before-after.png` per job; export short clips from
the editor and keep them with the evidence).

**Gate:** video link works logged out, shows only hackathon work, shows the full
pipeline, the editor, and the layered export. **Fallback:** the Phase 7 backup
recording, re-narrated.

## Phase 10 — Submission package *(must be last)*

**Work:** produce and check every item in section 7 of the brief: team, track,
problem statement, description, public repo with clean history and no secrets, the
video link, Meta-products and why-it-matters answers, feedback, and the optional X
link. Re-read the repo as a judge (README, history, assets); run the secret scan.
**Submit early on 3 Nov with everything except the X link, then edit the submission
before the deadline to add the best X post link** — edits are allowed until the
deadline (organizer answer, Discord #questions, 2026-10-27). Save the confirmation.
X post: Most Viral is counted through **Nov 8 EOD**, so the post can go live during the
event; build-in-public posts do not affect eligibility.

**Gate:** the form is submitted early on 3 Nov, edited with the X link before the
deadline, and a confirmation screenshot exists in `docs/`.
**Fallback:** if a field is not ready, submit the strongest honest version on 3 Nov
and improve it by editing before the deadline — late submissions are not considered.

---

## Risks

| Risk | Likelihood | Impact | Mitigation |
| --- | --- | --- | --- |
| Arabic shaping/fitting quality below demo bar | Medium | High | Phase 3 first; HarfBuzz + auto-fit; editor-first fallback |
| Muse Image edit drifts or refuses | Medium | High | Masked composite; classical inpaint; opaque cover |
| SAM finds bubbles, not lettering | Medium | Medium | Hybrid Spark-bbox → SAM box prompts; manual add |
| Cost per page higher than $0.05 | Low | Low | Measure in Phase 2; cache by hash; minimize calls |
| API outage or key issue during demo | Low | High | Recorded backup video + saved probe receipts |
| Time: vertical slice slips past 28 Oct | Medium | High | Cut to cover-instead-of-inpaint, keep the pipeline visible |
| Scope creep into "dashboard" | Medium | Medium | The editor is the product; no analytics screens |

## Validation

```bash
cd backend && python -m pytest -q
cd frontend && npm run typecheck && npm run build
python backend/scripts/smoke_sam.py assets/generated/test-panel.png   # one paid call
```

Per-phase evidence: probe receipts (`backend/.cache/probes/`), before/after PNGs
(`docs/evidence/`), and the numbers in `docs/submission-notes.md`.

## Budget

$150 credit. Estimated $0.023–0.032 per page, so the build can afford ~200 test
pages with room to spare. Spend is tracked from receipts; the expensive mistake to
avoid is re-running image edits to "look again" — save the output instead.

## Acceptance

- [ ] Phase 1 gate met and findings documented (no UNCONFIRMED left where a probe
      could answer).
- [ ] Phases 2–10 approved by the owner before they start.
- [ ] Each phase's gate has recorded evidence, or its fallback is in place and
      documented.
- [ ] The submission package exists, is checked, and was submitted on 3 Nov.
