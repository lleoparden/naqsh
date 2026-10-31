# Freeze check — 2026-10-31

Fresh clone of `main` at the freeze commit, Windows, README-only setup (Python venv,
`pip install`, `npm ci`, `npm run build`).

- Demo mode: `/api/health` through the Vite proxy **200**; comic fixture replayed
  **demo: true**, 39.8 s recorded.
- Live mode: `.env` copied privately (never printed), `LIVE_MODE=1`, one comic through the
  UI with Playwright: **58.8 s wall**, receipt **58.763 s / $0.037948**, no console errors,
  editor opened.
- Receipt: `docs/evidence/final-fresh-clone.json`.
- Server stopped; clone deleted including `.env` (confirmed missing).

Tag **v1.0** after this evidence PR merges.
