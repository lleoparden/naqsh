# Live-first video — recording guide (2026-10-31)

The video must show the working product with **live Meta model calls**. Demo replays are a
labelled fallback only. The **owner runs the takes**; the agent does not drive the camera.

## Preflight

```powershell
# terminal 1 (repo/backend) — LIVE
$env:DEMO_MODE='0'; $env:LIVE_MODE='1'
uvicorn app.main:app --port 8000

# terminal 2
cd frontend; npm run preview -- --port 4174
```

- Confirm the banner: `=== Naqsh LIVE MODE — paid model calls ENABLED ===`.
- Health: `http://127.0.0.1:4174/api/health` → 200.
- Browser Chrome 1920×1080, zoom 100 %, OBS 30 fps, notifications off.
- `.env` has `MODEL_API_KEY`; never show it on screen or in the terminal.

## Takes (all live unless marked)

1. **Comic — hero** (3 bubbles + caption): upload `fixtures/test-suite/pages/comic-three-bubbles.jpg`
   or a demo candidate. Show the **LIVE** banner, stage progress (read → segment → plate →
   verify → typeset), then the result and the receipt with seconds and cost.
2. **Menu** (`fixtures/test-suite/pages/menu-prices.jpg`): dense regions, prices/digits,
   receipt visible.
3. **Editor** on the comic result: layers (scenery/bubbles/text), hide/show, rename, drag,
   slider, Arabic style switch, export menu, ZIP download.
4. **Terminal log** (optional, 5 s): the server line
   `…: background bubbles=N sam=N box_fallback=N` plus the request 200, to prove the calls
   were live.
5. **Demo fallback** (only if a live take fails): start demo mode, show the **Demo mode**
   badge, say it is a recorded replay. Never present it as live.

**Wait handling:** record the real wait; cut between stages with a visible **“sped up 4×”**
or **“cut”** label and a timer. Do not speed up the whole video and imply real time.

## Budget

Three live takes, owner-run, expected **≈$0.60 total** (worst case ~$0.05–0.10 per take
with retries). Demo fallback is $0.

## What NOT to claim

- No time-saved ratio or multiplier; **“faster”** at most (owner baseline removed).
- No “fully automatic”, “no editing needed”, “any language”, “works on photos”.
- No clean-plate success on the photo label; show it as the honest limit if used.
- No “live” label on a demo replay; the badge must stay visible.
- No slides; only the real UI and terminal.
- No visual-quality claim about the offset close-up (demo cache predates the fix).

## After

Save to `L:\naqsh-review\video\`, add the link to `docs/submission-notes.md`; verify logged
out. The X post must exist before the deadline.
