# Status — 2026-10-29 (pre-recording)

One line per item; status is DONE / NOT STARTED / BLOCKED ON OWNER.

| Item | Issue / PR | Status | Evidence |
|---|---|---|---|
| Spark region names on crops | #98 / #107 | **DONE** | one SAM-backed naming call per page; names cached in the document and shown in Layers; evidence `docs/evidence/ui/region-names.json` |
| UI polish pass (states, spacing, state component) | #99 / #108 | **DONE** | one `StateIllustration` for loading/empty/success/error; screenshots `L:\naqsh-review\group3\` |
| `docs/feature-plan.md` | #100 / #109 | **DONE** | batch mode, layers-only, extra RTL, gates/fallbacks/effort, rubric ranking, cut order |
| `docs/hosting-plan.md` | #101 / #110 | **DONE** | five host options, $3/day live cap, per-IP limits, paused banner, 8–12 h estimate, owner steps |
| Time-saved ratio | #9 / — | **REMOVED** | owner decision 2026-10-29: not an editor; no ratio claimed, only “faster” |
| Clean-plate gate (#3) | #3 / — | **DONE** | owner closed #3 as completed on 2026-10-29; risk #4 (ghost/smear) remains open |
| Browser click-through (#8) | #8 / — | **DONE** | owner closed #8 as completed on 2026-10-29 |
| Official-rules question (#10) | #10 / — | **DONE (owner-closed)** | owner closed #10 on 2026-10-29; outside-tools and live-URL answers are still not recorded anywhere |

Notes:

- The clean-plate gate was closed by the owner; the ghost/smear risk **#4** is still open.
- No time-saved ratio is claimed; saying **faster** is allowed. The demo script and
  recording guide repeat this.
- Live mode is opt-in (`LIVE_MODE=1`); demo replay is the default and needs no key.


## 2026-10-31 (part 2) — judge-path hardening

| Item | Issue / PR | Status | Evidence |
|---|---|---|---|
| Spark region names | #98 / #107 | **DONE** | names cached in the document and shown in Layers; `docs/evidence/ui/region-names.json` |
| UI polish pass | #99 / #108 | **DONE** | state component + spacing; `L:\naqsh-review\group3\` screenshots |
| ~8 px after-side offset, browser re-check | #136 / #141 | **DONE (fix landed; demo cache NOT rebuilt)** | reproduced at 1:1 (source y=299 vs composite y=294), coverage/line-band fix + tests; offline recheck on live job 5313ddafca2e; demo cache still holds old composites |
| Demo candidates v2 | #178 / #181, #182 | **DONE — 6 pages, 2 pass / 4 fail** | live prefilter `docs/evidence/demo-v2/summary.json`; contact sheet `L:\naqsh-review\demo-candidates-v2\contact-sheet.jpg` |
