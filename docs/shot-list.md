# Shot list — silent capture (1920×1080, LIVE_MODE=1)

Owner records and edits in Recordly. **No narration**; hold each still for 2 s, keep the
cursor still during waits. Every claim below is from `docs/claims.md`; every number from a
receipt.

## Pre-flight

- [ ] Backend on 8000 with `LIVE_MODE=1`, `DEMO_MODE=0`; banner reads
      `Naqsh LIVE MODE — paid model calls ENABLED`.
- [ ] `frontend` built; preview on 4174; Chrome 1920×1080, zoom 100 %, clean mode
      `?clean=1`; toolbar/bookmarks hidden.
- [ ] `.env`, keys, private paths (`L:\...`, `C:\Users\...`) never on screen; terminal font
      large enough, history cleared.
- [ ] Selected pages: **PAGE_A = phase1-baker**, **PAGE_B = comic-a**, **LIMITS = Zion**.
- [ ] Budget: three live takes ≈$0.60 worst case; record cost from the receipt each time.
- [ ] Test offline before shooting: `pytest -q`, `npm run typecheck && npm run build`.

## Clips

| # | Duration | Actions | Must be visible | Must NOT be visible | Claim / receipt |
|---|---|---|---|---|---|
| 1 | 10 s | Empty app at `/?clean=1`; slow pan over title and drop zone; cursor still. | Empty upload state, title, LIVE-mode server implied. | Key, `.env`, private paths. | “Arabic-first layer editor.” |
| 2 | 45–75 s | Upload PAGE_A (`assets/generated/test-panel.png`); record the full live run; hold on stages. | Stage progress, LIVE banner, total seconds and cost. | Terminal key material; other pages. | Live run receipt: **63.8 s, $0.0417** (cache; fresh run may vary 29–62 s / $0.026–0.040; record actual). |
| 3 | 8 s | Cut to terminal: startup banner + request line. | `LIVE MODE` banner, one 200 request. | API key, env vars, user path. | “Live Meta model calls.” |
| 4 | 12 s | Before/after slider from 0 to 100 and back; 2 s holds at both ends. | Frame continuity, Arabic/English sides. | Any 100 % divider close-up claim. | “Outside the edited text areas, exported pixels are identical to the original” (max diff 0, three jobs). |
| 5 | 30 s | Editor tour: select a region, edit Arabic, change font and size, toggle an eye, drag a layer; hold. | Layers panel, text edit, font/size controls, drag. | Private paths. | “Every region is editable.” |
| 6 | 8 s | Switch Arabic style once (Egyptian → MSA); hold. | Style select, text change. | Re-translate cost claims. | “Switch register without re-running the page.” |
| 7 | 15 s | Cover patch + eyedropper (only if it worked in testing); undo. | Ellipse/rect patch, colour control, eyedropper. | Any claim it fixes photo plates. | “Manual cover for artwork the model should not touch.” |
| 8 | 15 s | Export menu, run ZIP, open `layers.json` / SVG in an editor; hold. | Export options, toast with size, layered SVG. | Flattened-image claim. | “Layered SVG + ZIP with layer manifest.” |
| 9 | 45–80 s | Upload PAGE_B (`fixtures/demo-v4/pages/comic-a.jpg`); full live run; hold on result. | 3 bubbles + caption, stage progress, cost. | Other pages. | Live receipt: **39.9 s, $0.0297** (ranges in claims). |
| 10 | 10 s | Receipt panel: seconds, cost, models per stage; 2 s hold. | `total_ms`, `total_cost_usd`, stage model names. | Key, env. | Same receipt numbers. |
| 11 | 15 s | Upload LIMITS (Zion poster); let it finish; hold on artifacts. | Visible ghost lettering/artifacts; label “LIMITS”. | Presenting it as clean. | Limits: decorative lithograph lettering leaves artifacts (`docs/evidence/demo-v3/summary.json`). |
| 12 | 8 s | Close on repo URL and README quickstart; hold. | `github.com/lleoparden/naqsh`, quickstart. | Private paths. | “Runs from the public repo; judges can run it.” |

## Rules

- No time-saved ratio; “faster” at most.
- Do not hide the demo badge if a replay is used; this shoot is live-first.
- If a live take fails, use the labelled demo replay as a fallback and say so in the log.
- Every clip gets a row in `docs/shot-log-template.md`.
