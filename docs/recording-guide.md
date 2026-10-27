# Recording guide (one page)

For recording the demo video. Demo mode replays **real cached runs**; it is labelled
on screen. The final video must include **at least one live run** — that is a rule,
not a suggestion.

## Setup

- Start the backend with demo mode on: `set DEMO_MODE=1` then
  `cd backend && uvicorn app.main:app --port 8010`.
- Build once: `cd frontend && npm run build && npm run preview -- --port 4174`.
- Browser: Chrome, **window 1920×1080** (full screen, `F11`), **zoom 100%** (Ctrl+0),
  clean mode on: `http://localhost:4174/?clean=1`.
- OBS: canvas 1920×1080, 30 fps, record the window, cursor visible. Hide notifications.
- Load the fixture first so the upload dialog opens in the repo folder
  `assets/generated/fixtures/`.

## Flows to record

1. **Page in / out with slider** — upload `01-comic-flat.png`. The badge appears;
   stages tick for ~48 s at the recorded pace; the result shows before/after. Drag
   the before/after slider left and right at 100% zoom.
2. **Menu** — upload `03-menu-paper.png` (~96 s). Point at the prices keeping their
   Latin numerals and the dot leaders gone.
3. **Editor: edit / register / skip / nudge / cover / undo** — click *Open editor*.
   Select `t1`, change one word, press Tab; switch the register and re-translate one
   region (shows the cost); skip a region; drag one box; draw a cover patch; Ctrl+Z
   twice. Reload the page to show the edits persisted.
4. **Receipt** — scroll to the receipt: per-stage milliseconds and cost. Say the
   number out loud ("this page cost $0.0233 and took 48 seconds, and these are the
   recorded numbers").
5. **SVG export** — click SVG, open it, show the text layer is selectable; then the
   Bundle ZIP: fonts + licences + outlined variant.
6. **Failing photo page (honest limit)** — upload `05-label-kraft.png`; the plate
   smears brown over the jar. Say plainly that photographed labels still fail and
   that this is why the editor has a manual cover tool.
7. **One live run** — disable demo (`DEMO_MODE=0`, restart the backend), upload a
   page, and let it run for real. Keep this in the final cut.

## Order that cuts well

Live run first (proof it is real) → menu → editor edit → SVG → failing photo →
close on the receipt. Keep the badge legible whenever demo mode is on.

## What not to do

- Do not hide the badge, crop it out, or claim a replay is live.
- Do not speed up the replay; it already runs at the recorded pace.
- Do not show the failing page as a success; it is the honest limit.
