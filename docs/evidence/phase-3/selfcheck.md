# Phase 3b — Muse Spark visual self-check

2026-10-27, Cairo. Design, live runs, and the injected-fault test.

## What it does

After the Arabic is drawn, one vision call looks at 100%-zoom crops of every
region (labelled with id, source text, and the Arabic actually drawn) and returns
per region:

```json
{"id": "t1", "ok": false, "issue": "overflow|clipping|unreadable|bad_translation|none", "note": "…"}
```

If anything is flagged, the pipeline makes **one** fix pass — shrink the layout to
80% for fit issues, re-ask Spark for a corrected line on `bad_translation` — then
re-renders and re-checks once. It never loops. Every run records `flagged`,
`fixed`, `retranslated`, `still_flagged`, cost and time.

## Live runs (both clean, nothing flagged)

| Page | Self-check flagged | Fixes | Still flagged | Self-check cost | Total page cost | Time |
| --- | --- | --- | --- | --- | --- | --- |
| comic, Egyptian | none | 0 | 0 | $0.001982 | $0.0399 | 88 s |
| menu, Egyptian | none | 0 | 0 | $0.0020 | $0.0507 | 130 s |

So on the demo pages the check adds ~$0.002 and no fixes — that is the *clean-run*
result, which says nothing about detection. Hence the test below.

## Injected-fault test (the honest measurement)

Twelve deliberate faults were drawn onto real region crops from the comic page —
3× overflow (1.55× size), 3× clipping (shifted so ascenders cut), 3× unreadable
(0.2× size), 3× wrong Arabic that fits — plus six clean crops (comic + chalkboard)
to measure false positives. One montage, one vision call, $0.0108.

| Metric | Value |
| --- | --- |
| Injected regions | 12 |
| Caught (any issue) | **11 / 12 — 91.7 %** |
| Correct issue class | **8 / 12 — 66.7 %** |
| False positives on clean | **0 / 6 — 0 %** |

By class:

| Fault | Caught | Correct class | What happened |
| --- | --- | --- | --- |
| overflow | 3/3 | 3/3 | reliable |
| unreadable | 3/3 | 3/3 | reliable |
| bad_translation | 3/3 | 2/3 | one called "clipping" |
| clipping | 2/3 | 0/3 | called "overflow" twice, one missed |

**Reading it honestly:** the check is a good *"is something wrong here"* detector
(91.7 %) and a mediocre *classifier* (66.7 %). It confuses clipping with overflow,
so a clipping flag still triggers the shrink fix — the right action for the wrong
label — and it missed one clipped case entirely. Translation checking works when
the Arabic is clearly unrelated, but it is not a translation QA system.

This is an injected-fault test on 12 regions from one page; it is not a benchmark
and the sample is small. It says nothing about real ghosting, colour errors, or
languages other than Arabic.

## Files

- `fault-injection.png` — the labelled montage that was sent to the model
- `fault-injection.json` — every row with truth vs prediction, plus the raw reply
