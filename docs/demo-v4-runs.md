# Demo sources v4 — live runs (item 4)

Criteria before running: requested English spelled exactly and fully visible, flat style,
2–4 regions, no digits/curves. Four `a` variants passed the visual check and were
transcribed; `b` alternates are kept but not selected. The Phase 1 baker source
(`assets/generated/test-panel.png`) exists and was run too.

| Page | Recall | CER | Bubbles | Seconds | Cost | Verify |
|---|---|---|---|---|---|---|
| comic-a | 0.75 | 0.0 | 3 | 32.0 | $0.0300 | clean beige/orange shapes, no text |
| shop-a | 1.00 | 0.0 | 0 | 42.0 | $0.0381 | letter outline fragments, partial BOX, clipped bottom |
| label-a | 1.00 | 0.0 | 0 | 44.4 | $0.0411 | dark border line; cropped letter tops at bottom |
| postcard-a | 0.50 | 0.0 | 0 | 48.8 | $0.0404 | SEASIDE POSTCARD fragments top/bottom; second line still visible |
| phase1-baker | 1.00 | 0.0 | 2 | 35.7 | $0.0287 | empty caption and bubbles, no text |

- All under 60 s. Reading (CER) is perfect where matched, but **comic-a and postcard-a have
  recall < 1** (one region unmatched/split), and **shop/label/postcard leave visible
  fragments**.
- Phase 1 baker is the cleanest (recall 1.0, CER 0, 2 bubbles, no residual).
- Live cost **$0.1783**; images **$0.08**; total **$0.2583** of $0.60.
- Contact sheets: `L:\naqsh-review\demo-v4\originals-sheet.jpg` and
  `results-sheet.jpg` (the three WPA posters are included as limits candidates; Zion is
  labelled owner-preferred; none re-run).
