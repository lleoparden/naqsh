# Recording build — v1.1 freeze

## Tag and commit

- **Recording build:** current `main`
- **Verified commit:** **`8c95a4f`** (`Merge pull request #254 …`)
- **Tag:** **`v1.1`** — applied to `8c95a4f` after owner approval of this docs PR
- **Rule:** no code changes after this tag except a real bug found during recording, approved by the owner first.

## Merge history (facts, not a re-litigation)

| PR | What | Who | Result |
|---|---|---|---|
| #254 | v2 mascot product integration | **owner, deliberately** | merged |
| #239 | earlier mascot product integration | **agent, by mistake** — branch was cut from the wrong base (`feat/mascot-product`) and merged with the v2 PR | merged, then reverted |
| #250 | revert of #239 | **agent** | merged; #239 code removed from main |

The Vectr palette retheme and the mascot are intended parts of the product on current
`main`. `v1.0` (`04e14fa`) is **not** the recording build: it predates the retheme and the
mascot integration.

## Verification (current main)

- **pytest:** 90 passed.
- **typecheck:** pass.
- **build:** pass.
- **demo path Playwright:** pass; ZIP 9,337,550 bytes; no console errors; 61.5 s.
- **axe:** home 0, editor 0.
- **CI:** `41340881429` (CI) and `41340881464` (Smoke matrix) — success.
- **Fresh clone (README only):**
  - Demo proxy health 200; comic replay `demo: true`, 39.8 s recorded.
  - Live comic, `LIVE_MODE=1`, `.env` copied privately and never printed:
    **74.2 s wall**, receipt **73.685 s / $0.040345**, **0 console errors**, editor opened.
  - Receipt: `docs/evidence/final-freeze-v1.1.json`.
  - Clone deleted including `.env` (confirmed missing).
- **Mascot states:** header idle/hover, loading, empty, success, error; counts 1/2/1/2/2
  as expected. `?mascot=off` → 0 nodes; `VITE_MASCOT=off` build → 0 nodes.
- **Overlap geometry at 1920×1080:** mascot boxes vs editor canvas SVGs — **no intersections**.
  Receipt/cost text is in the right panel and was not covered.
- **Demo cache under the new theme:** `phase1-baker` 39.795 s, `comic-v4` 39.872 s,
  `zion-limit` 80.386 s — all `demo: true`; screenshots in `L:\naqsh-review\freeze\`.
- **Limits:** no visual pass is claimed; an injected 500 for the error-state test appears
  as a console error in that harness only. Live UI reported none.

## After the tag

No code changes after `v1.1` except a real bug found during recording and approved by the
owner. Documentation-only corrections need owner approval too.
