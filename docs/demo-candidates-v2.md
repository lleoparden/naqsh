# Demo candidates v2 — diagnosis of v1 (no spend)

Owner verdict: all five v1 candidates were "extremely bad"; the Arabic itself is fine.
This is based on the contact sheet at `L:\naqsh-review\demo-candidates\contact-sheet.jpg`
and the v1 sources/receipts, plus the clean comic and chalkboard in the English suite.

## What went wrong, page by page

| v1 page | Source style | What the sheet shows | Likely stage |
|---|---|---|---|
| comic-bakery | flat vector but very detailed shop interior | English text drawn straight over the art; “CHAPTER ONE” collides with a bubble; Arabic is small and sits on busy shelves; the caption is empty | **text integration** (no bubble/panel behind text), plus fit-to-box shrinking |
| bakery-poster | gradient/painterly poster with wheat and sun | text floats on a plain field but Arabic is much smaller than the English and low-contrast; “FRESH LOAVES / 07:00–19:00” is lost in the illustration | **fit/contrast**, not reading |
| cafe-menu | textured paper with stains and vertical rules | Arabic is nearly invisible (light on cream); numbers reverse (4.25 → 25.4, 08:00 → 00:80); the page reads as an empty form | **contrast colour + bidi digits**, not detection |
| honey-label | painterly vector with gradients/shadows | Arabic is small and sits on a busy jar label; the label plate is smeared; digits stack oddly | **plate on a textured/painterly surface** + fit |
| night-market | painterly night scene with lanterns | **English ghost remains** (“NIGHT MARKET”, “FRIDAY 18:00”) and the Arabic sits on top; low contrast against sky | **plate/erase failure**, then contrast |

## What the clean pages have in common

The baker comic and the chalkboard (English suite) are **flat colour, thick dark outlines,
plain areas behind the text**, and the text sits inside a bubble/board area rather than on
detail. The v1 candidates were mostly **painterly or textured**, and even the flat comic
had text placed over shelves, not inside bubbles.

## Finding

1. **Primary cause is text integration, not Arabic or reading**: v1 drew English at
   arbitrary boxes on the artwork with no bubble/panel. The model then set Arabic in the
   same box over the art, so it looks pasted on, shrinks to fit, and loses contrast.
2. **Secondary cause is the source art**: painterly gradients, paper stains and photographic
   surfaces give the plate model texture to smear, leave ghosts (night market) and make
   digit bidi/contrast worse.
3. **Contrast and digits**: the menu shows light-on-cream Arabic and reversed decimal/time
   digits; the night market shows English ghosts.

## Rules for v2 (no pipeline tuning)

- Source art: flat vector only, solid fills, thick black outlines, 4–6 colours, no
  gradients/texture/photos, plain empty background areas.
- **We draw the text containers** (speech bubbles, caption banner, label panel, postcard
  panel, chalk text) in code over the flat art, so every text area is plain and
  high-contrast by construction.
- Large English text, 2–4 regions, no digits/prices, no curved or rotated text.
- Ground truth is the code-drawn box/text.

This is a data/art fix, not a pipeline change.
