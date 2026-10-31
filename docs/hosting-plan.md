# Hosting plan — NOT NEEDED (organizer answer 2026-10-31)

**Status: NOT NEEDED.** A public live URL is not required; judges run the project from the
README and watch the 3-minute video. This plan is kept only as an optional appendix.

Relayed by the owner from Cerebral Valley: **a hosted URL is better for judges** than a
video-only submission. This is a plan; nothing is deployed. Do not deploy until the
live-URL question is answered.

## Constraints

Backend: Python 3.12, FastAPI, OpenCV headless, `uharfbuzz`, `freetype-py`, Pillow, numpy;
repo ~101 MB tracked, demo cache ~11 MB; uploads up to 15 MB, max side 6000 px; model key
must stay server-side. Frontend: static Vite bundle served by the same host.

## Options

| Option | Free / cheap tier | Fit | Build / start | Cold start | Notes |
|---|---|---|---|---|---|
| **Fly.io** | ~$5 free credit, pay-as-you-go | Good: Docker + volume for cache | `docker build`; `uvicorn app.main:app --host 0.0.0.0 --port 8080` | ~1–3 s if `min_machines_running=1` | Easiest secrets + one region close to users |
| **Render** | Free web service (sleeps), paid ~$7/mo | Good; Docker or Python buildpack | build `pip install -r requirements.txt`, start uvicorn | 30–60 s on free (sleeps) | Free tier cold start is bad for judges; paid fixes it |
| **Railway** | Trial credit, ~$5/mo typical | Good Docker support | same | seconds | Simple env vars, usage-based |
| **VPS (Hetzner/DO)** | ~€4–6/mo | Full control, must manage TLS/proxy | docker compose + Caddy | none | Most work; best for a long-lived URL |
| **Hugging Face Spaces** | Free CPU | Docker SDK works, but 16 GB RAM / 50 GB disk and public repo assumptions | Dockerfile | ~30 s + rebuild | Key handling is awkward for a public Space; least suitable |

**Recommendation:** Fly.io or a small VPS if the URL will be live for weeks; Render paid if
simplicity matters more than $7. Free tiers are acceptable only if the video shows a
warm-up run.

## Safety

- Key only in host secrets (`fly secrets set MODEL_API_KEY=…` / Render env var); never in the
  image, repo, or client.
- **Global daily live-run cap in code**, default **$3/day** (count live `/api/localize` jobs
  and `/api/retranslate` calls by recorded cost; reset at UTC midnight; persist to a small
  file/volume).
- **Per-IP limit:** e.g. 3 live runs/hour and 10/day per IP; demo replays do not count.
- When the cap is hit: HTTP 429 plus a visible **“Live runs paused — demo replay still
  works”** banner; demo fixtures keep replaying.
- Max upload 15 MB, sides ≤6000 px, MIME sniffing plus Pillow verify (already implemented
  server-side); reject non-images early.
- Demo mode stays **on by default** for the public URL (`DEMO_MODE=1`); live only for
  unknown uploads inside the cap.
- CORS limited to the deployed origin; no `/docs` in production if it can be avoided.

## Judge experience

1. Open URL → pick one of the five fixtures → replay with the demo badge (48 s comic,
   62 s menu at recorded pace).
2. Upload an unknown page → live run within the cap, with the existing stage list and
   progress; expected 60 s comic, ~60–80 s menu warm.
3. If the cap is reached → clear paused message and the fixtures still replay.

## Effort and cost

- **Estimate: 8–12 h** for Dockerfile, cap/limiter code, deploy, TLS, smoke tests, and a
  hosted smoke checklist.
- **Monthly:** $0 (free tier, sleeps) to **$7** (Render paid / Fly small), or ~€5 VPS.
- If it slips: **cut hosting entirely** and submit the video plus local demo; the plan is
  explicitly last in priority and depends on the pending live-URL answer.

## Step list for the owner

1. Confirm the live-URL answer (PENDING with CV).
2. Create the host account; add `MODEL_API_KEY` as a secret only.
3. Deploy the image; set `DEMO_MODE=1`.
4. Set the daily cap ($3) and per-IP limits; verify the paused banner by temporarily
   setting the cap to $0.
5. Upload one known fixture (expect badge) and one unknown image (expect live, within cap).
6. Check cold-start time and record it in `docs/submission-notes.md`.
7. Add the URL to the submission as a backup link; keep the video as the primary artifact.
