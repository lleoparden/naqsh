# Status — 2026-10-29 (pre-recording)

One line per item; status is DONE / NOT STARTED / BLOCKED ON OWNER.

| Item | Issue / PR | Status | Evidence |
|---|---|---|---|
| Spark region names on crops | #98 / #107 | **DONE** | one SAM-backed naming call per page; names cached in the document and shown in Layers; evidence `docs/evidence/ui/region-names.json` |
| UI polish pass (states, spacing, state component) | #99 / #108 | **DONE** | one `StateIllustration` for loading/empty/success/error; screenshots `L:\naqsh-review\group3\` |
| `docs/feature-plan.md` | #100 / #109 | **DONE** | batch mode, layers-only, extra RTL, gates/fallbacks/effort, rubric ranking, cut order |
| `docs/hosting-plan.md` | #101 / #110 | **DONE** | five host options, $3/day live cap, per-IP limits, paused banner, 8–12 h estimate, owner steps |
| Baseline protocol + time-saved results table | #9 / — | **BLOCKED ON OWNER** | protocol in `docs/baseline-protocol.md`; `docs/time-saved.md` table is empty/PENDING until the owner records a manual baseline |
| Clean-plate gate (#3) | #3 / — | **BLOCKED ON OWNER** | gate needs the owner to inspect the plate at 100 % zoom; risk tracked in #4 |

Notes:

- The clean-plate gate is **not** a code task; the risk issue #4 stays open until the owner
  judges the plate.
- No time-saved ratio may be claimed until the baseline row exists; the demo script and
  recording guide repeat this.
- Live mode is opt-in (`LIVE_MODE=1`); demo replay is the default and needs no key.
