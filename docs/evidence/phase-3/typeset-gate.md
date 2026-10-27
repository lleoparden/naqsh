# Phase 3a gate — RTL typesetting (HarfBuzz)

Run 2026-10-27, Cairo. Six runs: comic, menu, chalkboard, each in Egyptian and MSA.

## What changed

- **Shaping:** HarfBuzz shapes every line (joining, ligatures, mark placement) and
  FreeType rasterises the glyph ids. Western digits and Latin words are shaped as
  separate LTR runs placed right-to-left, so `شاي 25` keeps 25 in order.
- **Fitting:** measured on shaped ink (ascenders, descenders, diacritics), wrapped
  at word boundaries, two-line blocks balanced by smallest widest line, clamped only
  when the box cannot hold the text.
- **Fonts (all OFL, licences in `assets/fonts/` and ASSETS.md):** Tajawal
  Regular/Bold for speech, display and chalk; Noto Naskh for print/serif; Amiri as
  the calligraphic option. Cairo and Reem Kufi were tested and rejected for broken
  substitution; Noto Kufi is retired.

## Result

| Page | Register | Cost | Overflow |
| --- | --- | --- | --- |
| comic | egyptian | $0.0233 | none |
| comic | msa | $0.0230 | none |
| menu | egyptian | $0.0297 | none |
| menu | msa | $0.0452 | none |
| chalkboard | egyptian | $0.0250 | none |
| chalkboard | msa | $0.0362 | none |

**All 6 runs fit every region with no overflow by the fitter's own measurement**
(6/6 runs, 23 regions total). Six runs cost **$0.1823**, average $0.0304/run.

Contact sheet: `typeset-gate.png` — 100% crops labelled page / register / region /
family / size.

## What the sheet shows (owner judges)

- Comic: joined, balanced Arabic in both registers; caption and both bubbles fit.
- Chalkboard: strongest result — bold chalk lettering, correct digits, no clipping.
- Menu: all lines fit, but the small print (subtitle, footer) lands at 12–19 px and
  reads thin; the dish names are also small next to the prices. Legible, not pretty.
- MSA menu translates `FALAFEL` as `فلالفل` (transliteration) rather than `طعمية`;
  a translation-quality point, not a typesetting one.

## Known limits

- Size is capped by the box; if Spark's box is shorter than the line was, the Arabic
  gets small rather than overflowing. That is deliberate.
- Font matching is still a keyword map from Spark's style words, not a real matcher.
- Diacritics are placed by HarfBuzz, but no font we bundle is a full vocalised
  typeface; heavily vocalised text (tashkeel) is untested.
