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
  with a ≈16 px vertical offset, so the plate must be registered before compositing.)*

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

## Notable results and numbers

| Date | Number | How it was measured |
| --- | --- | --- |
| 2026-10-27 | API reachable from Cairo, first byte < 1 s (401 response) | `Invoke-WebRequest` timing during the reachability check |
| 2026-10-27 | Spark vision read: 6.8 s, 3,367 in / 435 out tokens, **$0.00606** | Probe receipt `spark-image-20261027T123659Z.json` |
| 2026-10-27 | Spark Arabic line: 2.0 s, 137 in / 268 out (204 reasoning), **$0.00131** | Probe receipt `spark-text-20261027T123630Z.json` |
| 2026-10-27 | SAM bubbles: 3.4 s, 2 masks, conf 0.961, **$0.0025** | Probe receipt `sam-20261027T123816Z.json` + overlay PNG |
| 2026-10-27 | Muse Image generate: 12.2 s, 1280×1920 out for a 1024×1536 request, **$0.01** | Probe receipt `image-generate-20261027T123645Z.json` |
| 2026-10-27 | Muse Image edit: 13.6 s, lettering gone, **$0.01**, ≈16 px page shift | `image-edit-…json` + local phase-correlation measurement |
| 2026-10-27 | **Phase 2 pipeline, generated page: 25–30 s, $0.0184–$0.0194 per page** | Per-stage receipts in `docs/evidence/phase-2/receipt-egyptian.json` |
| 2026-10-27 | Register comparison, same page | Egyptian `عيش طازة؟` / `كل يوم الصبح` vs MSA `خبز طازج؟` / `كل صباح` — same layout, same cost |
| 2026-10-27 | Clean-plate reliability: 4/7 runs clean, 2 ghosted, 1 smeared | Visual review of `docs/evidence/phase-2/failure-ghost-lettering.png` |
| _pending_ | **Time to localize one page by hand vs. with Naqsh** | Stopwatch protocol below |

### Time-saved measurement (the Impact claim)

Protocol — write it once, follow it exactly:

1. Pick three pages from the test set (one comic page, one poster, one menu).
2. **Hand baseline:** the owner localizes one page with their normal tools, timed
   with a stopwatch, from opening the file to exporting. Record the number and
   what "done" meant (text replaced, fitted, exported). Do this on camera if
   possible — it becomes B-roll for the video.
3. **Naqsh:** same page, same definition of done, timed from upload to export.
   Count manual corrections (each region edit).
4. Report: minutes hand vs. minutes with Naqsh, corrections per page, and the
   ratio. State the sample size honestly (n=3, one operator).

## Media worth using (screenshots / clips)

Collect as we go; each entry says what it proves.

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
