# Backup video — recording guide (pre-recording, 2026-10-29)

Goal: a 3:00 backup video that shows the real product, recorded before the deadline so a
bad live run cannot block the submission. **Do not claim a time-saved ratio** until the
owner's manual baseline exists (`docs/time-saved.md` is still PENDING).

## 1. Start the app in demo mode (no paid calls)

```powershell
cd backend
$env:DEMO_MODE='1'; $env:LIVE_MODE='0'
uvicorn app.main:app --port 8000

cd frontend
npm run build
npm run preview -- --port 4174
```

Open `http://localhost:4174/?clean=1` (clean hides the API-key status chip; the demo badge
stays visible). Browser Chrome, window 1920×1080 (full screen F11), zoom 100 % (Ctrl+0).

Never start a live-mode server (`LIVE_MODE=1`) without telling the owner first.

## 2. Pages and recorded waits

All five demo entries replay from real runs; timings and costs are the recorded ones:

| Page | Use in the video | Recorded total | Recorded cost |
|---|---|---|---|
| comic | hero: layers, bubbles, edit, export | **39.8 s** | $0.0280 |
| menu | dense page: 16 regions, scenery only | **90.3 s** | $0.0391 |
| chalkboard | second style: scene + text | **72.4 s** | $0.0445 |
| sfx-comic | captions + kept SFX | **42.6 s** | $0.0276 |
| label-fail | honest limit: photo label, plate not clean | **39.7 s** | $0.0269 |

Source: `fixtures/demo/*/receipt.json` (`total_ms`, `total_cost_usd`). On the demo server
the upload returns the recorded receipt; do not narrate those seconds as live waiting.

## 3. What the badge shows

A visible **Demo mode** chip: “replaying a recorded run — <fixture>”, plus “timings and
cost below are the recorded ones; this page did not call the model API”. Never hide it;
`?clean=1` does not remove it.

## 4. Takes

1. **Home** (`/?clean=1`, 5 s): title, Arabic style toggle, drop zone.
2. **Comic upload** (demo, badge visible): show the result, open Layers.
3. **Layers** (20 s): Scenery, 2 bubbles, 3 text; hide one bubble, show it, rename the
   title, drag a text layer.
4. **Edit** (20 s): change one line, switch register, reset to the AI result.
5. **Cover + colour** (15 s): draw an ellipse patch, change fill with the colour control.
6. **Export** (15 s): open Export, run PNG/SVG, show the size toast; mention the ZIP has
   `layers.json` + `layers/`.
7. **Menu page** (20 s): 16 regions, scenery-only background.
8. **Honest limit** (15 s): label-fail; say the plate is not clean on photographed labels
   and the editor is where you fix it.
9. **Close** (10 s): repo, test count, demo-mode honesty.

### DEMO vs LIVE_MODE=1

- **Default and safest:** every take above is DEMO (`DEMO_MODE=1`, `LIVE_MODE=0`). No key,
  no spend, badge honest.
- **Optional live take:** only after telling the owner, restart with
  `$env:LIVE_MODE='1'; $env:DEMO_MODE='0'`, upload the comic once (≈$0.03, ~37 s live),
  then restart demo mode. If live fails, the demo cut is already complete.
- Do not run live more than once for the backup.

## 5. What NOT to claim

- No time-saved ratio or multiplier. Saying **“faster”** is allowed; a number is not.
- No “fully automatic”, “no editing needed”, “any language”, “works on photos/branding”.
- No “the demo is calling the model live” — the badge is there because it is a replay.
- No clean-plate claim for the label-fail page; it is shown as a limitation.
- No visual-quality claim about a 100 %-zoom before/after divider: the demo cache predates
  the frame-offset fix, so avoid that close-up until the cache is rebuilt.

## 6. Before you record

- `pytest -q` green, `npm run typecheck && npm run build` clean (last: 88 tests).
- Servers on 8000/4174 only; no live-mode server running.
- Close notifications; cursor visible; keep the demo badge in frame.

## 7. After recording

Save the file outside the repo (`L:\naqsh-review\video\`), name it with the date, and add
the link to `docs/submission-notes.md`. The submission can be edited until the deadline;
after the deadline no edits are possible.
