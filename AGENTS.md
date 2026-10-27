# Naqsh — agent instructions

Read this before touching anything. It is the whole context a new agent needs.

## What Naqsh is

Naqsh (نقش) is an **Arabic-first visual localizer**. A user uploads an image (comic
page, poster, menu); Naqsh reverse-engineers it into editable layers, translates
the text into natural Arabic, removes the original lettering, re-typesets Arabic
right-to-left in the original style, and lets the user fix every region in a layer
editor before exporting layered SVG/PNG.

The users are Arabic webcomic creators, small publishers, and small businesses
with menus and posters. Most localization tools handle RTL badly, so these people
still localize by hand. Impact is the largest judging criterion, so every feature
must trace back to that user and to one measurable claim (time per page by hand
versus with Naqsh).

## The event (this explains the constraints)

Meta Global AI Developer Hackathon, virtual, run with Cerebral Valley.

- Kickoff 26 Oct 2026, 12 PM ET. Building runs through 4 Nov. **Submission due
  4 Nov, 9:00 PM ET = ~4:00 AM 5 Nov Cairo. Late submissions are not considered.**
- Internal targets: backup demo video by 30 Oct, feature freeze 1 Nov, submit 3 Nov.
- Track: Indie Developer, solo. Problem statement: **"Build for Your World."**
- Stage 1 is pass/fail: fits the problem statement and genuinely uses Meta's models.
- Stage 2 scores 0–10 on: **Impact 30%**, **Use of Meta AI tooling 25%**,
  **Technical depth 20%**, **Demo 25%**. Top 5 per track present the demo video live,
  so the video is the main judged artifact alongside the code and live product.
- Do not drift into the anti-project list: AI medical advice, basic RAG, simple
  image analyzers, Streamlit apps, dashboards as the main feature, education
  chatbots, resume screeners, nutrition coaches, personality/sports analyzers,
  anything political or war-related. Naqsh is a **layer editor**, not a dashboard.

Available Meta models: Muse Spark series, Muse Wonder, Muse Image, Muse Voice
Transcribe, SAM 3.1 (all via Meta Model API), open-weight Muse Glimmer / Muse Spark
Open, and the Muse Code agent. Budget: $150 of API credits.

## Hard rules (disqualification risks)

1. **New work only.** Every file is written during the hackathon. Do not copy code
   from the author's older projects (Vectr or anything else). Learning workflow
   conventions is fine; copying implementation is not. The README says what is new.
2. **The repository is public.** Never commit a secret. Keys live in `.env`
   (gitignored); `.env.example` is committed. Check `git diff --cached` for secrets
   before every commit. Never print a key, never echo `.env`.
3. **Only rights-cleared assets.** CC0/public domain, or generated with Muse Image.
   No copyrighted comics, manga, or Webtoon. Every asset and its license goes in
   `ASSETS.md` in the same commit that adds it.
4. **Commit history is judged.** Commit early, often, and with messages that say
   what changed and why.

## Stack and boundaries

- `frontend/` — React + Vite + TypeScript + Tailwind. The layer editor is the
  centerpiece of the UI; it is not a dashboard and not a form.
- `backend/` — Python + FastAPI. Owns all Meta Model API calls, prompt building,
  mask decoding, compositing, and export. The browser never sees the API key.
- Meta Model API base URL `https://api.meta.ai/v1`, Bearer auth.

Rules of the boundary:

- The frontend never calls `api.meta.ai` directly and never handles the key.
- The backend's job is pixels and geometry: segmentation masks, text region
  quads, cleaned plate, fitted Arabic layout, SVG layers. Keep that logic in
  testable pure modules, not in route handlers.
- Cost is a product constraint: every page must have a recorded cost. Cache
  model output by content hash while developing; never re-run a paid call to
  "see it again".
- Performance is a feature: uploading a page should produce a first result fast
  enough to keep a creator in the flow. Record real timings in
  `docs/submission-notes.md`, never estimates presented as measurements.

## Working with the Meta models

Facts confirmed against the docs and probes live in `docs/api-findings.md`. Read it
before designing a call. Non-negotiables learned there:

- SAM 3.1 returns geometry as **special-token text** (one line per frame: `<0f>`
  then `id<|box;...|><|mask;...|>` records); masks are base85 payloads with their
  own H,W and encoding marker. Request `one_bit` masks for smaller payloads.
- Muse Image edits by instruction; there is **no mask parameter**. Naqsh preserves
  artwork by compositing the edit back through SAM masks, not by trusting the model
  to leave the rest untouched.
- Anything not yet verified is marked **UNCONFIRMED** in the findings doc. Never
  present an unverified assumption as fact, in docs or in the demo.

## Branch, commit, and GitHub workflow

Re-created for Naqsh from the author's conventions; keep them.

- `main` is protected by habit: no direct commits for feature work. Branch names
  use a purpose prefix: `feat/`, `fix/`, `enhance/`, `update/`, `chore/`, `docs/`,
  followed by a short lowercase slug. One branch = one work item.
- **Commit messages:** Conventional Commits, imperative, scoped, with the phase in
  parentheses when it helps tracing:
  `feat(sam): decode base85 masks into per-region polygons (Phase 1)`.
  The body explains what changed, why, what was verified (commands, counts), and
  the limits left behind. Never squash or rewrite published history.
- Each phase owns one **epic issue**; each approved slice gets a **sub-issue**
  before code is written. Every branch, commit, and PR references its issue
  (`Closes #12`).
- PRs use `.github/PULL_REQUEST_TEMPLATE.md`, state the checks that were actually
  run, and end with a **self-review**: re-read the full diff, post what it really
  changes, the risks found, and any residual doubt. An unresolved doubt blocks the
  merge.
- Small, self-contained PRs may be merged by the agent with a merge commit once
  checks pass; anything touching the pipeline contract, cost, security, or public
  interfaces needs the owner's review.

## Documentation duties

- `docs/plan.md` — phases, gates, fallbacks. Do not start a phase after Phase 1
  without owner approval of this file.
- `docs/api-findings.md` — per model: what works, request/response shapes, latency,
  cost, rate limits, errors. Update after every probe run.
- `docs/submission-notes.md` — kept current **as work happens**, not at the end:
  which model does what and why it mattered, API friction/bugs, numbers (including
  the time-saved measurement), and the screenshots/clips worth using in the demo
  and the X post.
- `docs/DECISIONS.md` — dated record of choices that are expensive to reverse
  (model roles, inpainting strategy, export format, fonts).

## Commands

```bash
# backend
cd backend && uvicorn app.main:app --reload --port 8000
cd backend && pytest -q

# probes (each writes a JSON receipt to backend/.cache/probes/)
python backend/scripts/smoke_spark_text.py
python backend/scripts/smoke_spark_image.py assets/generated/test-panel.png
python backend/scripts/smoke_sam.py assets/generated/test-panel.png
python backend/scripts/smoke_image_generate.py
python backend/scripts/smoke_image_edit.py assets/generated/test-panel.png

# frontend
cd frontend && npm run dev
cd frontend && npm run build && npm run typecheck
```

## Definition of done

The approved scope works end to end, the checks were actually run in this session,
the docs above are current, no secret is staged, and the demo path (upload →
layers → edit → export) is something a judge can click through without help.

## Standing rules for tasks (added 2026-10-27)

These apply to every work item, without being repeated in the task.

### Self-check before you report

After every work item, before writing the report:

1. List each acceptance criterion from the task as **PASS / FAIL / NOT TESTED** with the
   evidence that decides it (command + output, file, receipt, screenshot).
2. Run `cd backend && pytest -q`, and for frontend tasks `npm run typecheck` and
   `npm run build`; run lint if the task touches linted code.
3. For pipeline work, run it and look at the output images before claiming anything.
4. Check the numeric gates against `docs/plan.md`; if a gate fails, stop and propose the
   documented fallback instead of pushing through.
5. Run the rules check: no secrets staged (`git diff --cached` scanned), no unlicensed
   assets, `ASSETS.md` updated for anything new, no code from `L:\vectr`, README
   "What's new" still accurate.
6. Update `docs/submission-notes.md`.
7. Re-read the full diff before committing; post a self-review on the PR.

Report using this exact structure: **What I did / Evidence / Gate status / What I did
NOT verify / Risks / Cost / Next step.** Do not claim a visual pass; state that the
owner judges images.

### Merge hygiene

- No direct pushes to `main`. Branch, PR, merge commit.
- Do not merge while CI is red or **pending**; wait for every required check.
- Hand-written commit titles; never pass a PR-body file to `git commit -F`.

### Budget

If the mandated work cannot fit under the task's API budget cap, stop and ask before
overrunning. Do not silently exceed a cap.

### Decisions that belong to the owner

Ask, do not choose silently, on: translation register defaults, scope cuts, anything
touching the hackathon rules or submission form, and any public-facing claim or number.
