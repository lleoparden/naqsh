# After-side offset — investigation

Date: 2026-10-28. Owner reports the "after" side looks ~8 px higher than the original at
the before/after divider when seen in the browser.

## What was measured

The on-screen canvas was screenshotted at **exactly 100 % zoom** (viewport sized so the
fit calculation lands on 1.0) at device pixel ratios **1, 1.25, 1.5 and 2**, with the
slider fully on the original and fully on the after side. For every column across the
comic frame, the first dark row (frame top edge) was compared:

| DPR | Screenshot size | Columns compared | Δy between before and after |
|---|---|---|---|
| 1 | 1280×1921 | 90 | **0** |
| 1.25 | 1600×2401 | 90 | **0** |
| 1.5 | 1920×2882 | 90 | **0** |
| 2 | 2560×3842 | 90 | **0** |

At 106 % zoom (stepped with the zoom buttons) the same test over 85 columns also gives
**Δy = 0**.

Exported pixels were already proven equal outside the text coverage (max diff 0, see
`docs/evidence/ui/after-alignment.json`).

## Conclusion

The offset is **not reproducible** in headless Chrome at 100 % (fit), 106 %, DPR 1–2, or
with fractional DPR values that mimic Windows display scaling. Before and after use the
same `<image>` geometry inside one SVG (`x=0, y=0, width=doc.width, height=doc.height`),
and the original is clipped with a `<clipPath>` rect, not re-positioned, so there is no
code path that could shift one side by 8 px.

## What would be needed to proceed

If the offset is still visible on the owner's machine, it is outside what this harness can
reproduce. Needed: browser + version, OS display scaling, browser zoom, the exact job id,
and a screenshot of the canvas. Possible remaining suspects are GPU compositing of the
CSS-transformed canvas at fractional browser zoom, or a monitor/OS-level artifact — not
the page geometry, which measures 0.

Screenshots: `L:\naqsh-review\offset\canvas-{100,50,0}.png`,
`exact-dpr{1,1.25,1.5,2}-{0,100}.png`, `offset.json`, `exact.json`.
