# Fresh-clone test — 2026-10-31

Clone: `git clone --depth 1 https://github.com/lleoparden/naqsh.git` into
`L:\naqsh-review\fresh-clone-2026-10-31`, **outside** the repo. Deleted afterwards,
including the copied `.env` (confirmed missing).

Environment: Windows, **Python 3.12.10**, **Node v24.18.0**, npm **11.16.0**. No version
pins are documented in the README.

## What worked

- Clone succeeded; repo public.
- `python -m venv .venv` then `pip install -r requirements.txt`: clean; `fastapi, cv2,
  uharfbuzz, meta_sam_parser` import fine; fonts are in `assets/fonts`.
- `npm install`: 9 s, 85 packages, with a warning that `esbuild` postinstall scripts were
  not run (`npm warn allow-scripts`); `npm run dev` still started Vite in 342 ms on
  `localhost:5173` (IPv6 `127.0.0.1:5173` is refused).
- Backend demo mode on 8010: `/api/health` OK; comic fixture replay returned
  `demo: true`, 39.8 s, $0.0298.
- Live run (approved, one comic): copied `.env` privately, `LIVE_MODE=1`,
  `POST /api/localize` returned **61.637 s** receipt (**61.7 s** wall) and
  **$0.039521**. Server stopped; clone deleted.

## README problems found (exact)

1. **Port mismatch:** the demo command starts the backend on **8010**, but
   `frontend/vite.config.ts` proxies `/api` to **8000**. Result: the UI at 5173 gets
   **500** from `/api/health` and cannot demo. `NAQSH_API` exists but is undocumented.
2. **Shell syntax is Unix-only:** `DEMO_MODE=1 uvicorn …` does not work in PowerShell
   (needs `$env:DEMO_MODE='1'`), and `.venv/Scripts/activate` is the bash path
   (PowerShell needs `.venv\Scripts\Activate.ps1`). macOS/Linux need
   `source .venv/bin/activate`.
3. **Stale live-mode statement:** “anything else goes live” — now paid calls are blocked
   unless `LIVE_MODE=1`; the README never mentions `LIVE_MODE`.
4. **No quickstart at the top**, no Python/Node version pins, no note that a Meta API key
   needs a payment method.
5. **Demo instructions use `npm run dev`**, not the build/preview path used elsewhere; the
   API target is unstated.
6. **No troubleshooting** for the 8010/proxy mismatch, PowerShell activation, or npm
   allow-scripts.

## Not verified in this clone

- macOS/Linux setup (only Windows tested).
- The live UI path (only the API live call was run).
- Whether `npm run build` works with the blocked esbuild postinstall (dev server did).
