# Spend audit — 2026-10-28

The traceable total rose from **$2.7451** to **$2.8064** (+**$0.0613**) between the
Group 1 report and the theme pass. This audit names every unit of that delta.

## Two real jobs

| Job | Created (Cairo, from receipt mtime) | Cost | Page (first regions) |
|---|---|---|---|
| `86ad5b1e5514` | 2026-10-28 15:53 | $0.0253 | `CHAPTER ONE`, `FRESH BREAD?`, `EVERY MORNING` (comic) |
| `d381ebafa4a3` | 2026-10-28 16:08 | $0.0258 | same comic page |

Both are live uploads of the comic fixture (`01-comic-flat.png`). They were not created
by any script in this repository: the e2e scripts only call `/api/jobs/*` document,
layout, reset and cover endpoints, and the test suite never calls
`/api/localize` against the live client. They line up with the owner clicking through
the UI while the backend ran live (`DEMO_MODE=0`) on port 8000.

## Eight retranslate calls

`docs/evidence/api-spend.jsonl` entries at **2026-10-28T12:54:49–12:54:56Z**
(15:54 Cairo), all `retranslate 86ad5b1e5514/t1`, $0.0089 total. Eight clicks on one
region within eight seconds: that is the spam case, from the owner's manual testing of
the pre-Group-1 build (PR #84, which added the server throttle, merged at 13:23Z, after
these entries).

## Conclusion

**Not from tests or e2e.** The spend is manual UI use: two live uploads and eight
re-translate clicks made before the throttle existed. No repository script needs a fix
for this delta, but the suite is now hardened so it cannot happen from tests:

- `backend/tests/conftest.py` forces demo mode and clears the API key for every test;
  the live pipeline raises before any HTTP call unless a test is marked `@pytest.mark.live`.
- No test currently carries that marker.
- The e2e scripts only exercise document/layout/reset/cover/export endpoints; none calls
  `/api/localize` or `/api/retranslate`. A comment at the top of each script records that.

## Re-runs

`python backend/scripts/spend_report.py`:

```
pipeline jobs    79  $2.4443
demo replays     37  $0.8632  (recorded cost, not new spend)
probes           11  $0.0436
script ledger    69  $0.3185
TOTAL                  $2.8064
```
