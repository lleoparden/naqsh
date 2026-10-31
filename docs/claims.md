# Public claims — allowed sentences and evidence

Date: 2026-10-31. Use only these; every sentence points at evidence.

## (a) Pixel claim

**Allowed:** “Outside the edited text areas, exported pixels are identical to the
original.”

- Coverage definition: **mask ∪ ink extent ∪ reading box, dilated** — the pixels the
  pipeline is allowed to replace.
- Measurement: `docs/evidence/ui/after-alignment.json`; source vs composite outside
  coverage, three jobs:

  | Job | Outside px | Max diff |
  |---|---|---|
  | comic `d3dbface16b8` | 1,656,284 | **0** |
  | menu `e13f9585b24f` | 156,871 | **0** |
  | sfx `6a8aa7a0829b` | 1,881,172 | **0** |

- Do **not** say “the cleaned plate is identical to the original.” The raw Muse Image
  plate is a **full-page re-render** and differs outside the masks too (v2 measured mean
  abs 2.49–7.38 outside masks). Only the **composite/export outside coverage** is identical.

## (b) Cost and time

**Allowed:** “A comic page costs about **$0.026–0.040** and takes about **29–62 s**; a
menu page costs about **$0.037–0.066** and takes about **62–122 s**.”

Evidence: `fixtures/demo/comic/receipt.json` ($0.0280/39.8 s),
`fixtures/demo/menu/receipt.json` ($0.0391/90.3 s),
`docs/evidence/phase-8/variance-summary.json`,
`docs/evidence/live-ui-fresh-clone.json` (48.4 s/$0.027682),
`docs/evidence/fresh-clone-2026-10-31.md` (61.7 s/$0.039521).

## (c) Limits — say these plainly

- Flat, stylised art works best (comic, flat poster, chalkboard, printed menu).
- **Photographed or painted textures** can leave smears/ghosts (`label-fail`).
- **Curved or rotated text** is read but set straight.
- **Handwriting** is read inconsistently and the plate leaves marks.
- **Decorative lithograph/WPA lettering** leaves ghost/visible lettering (v3 posters;
  `docs/evidence/demo-v3/summary.json`).
- No time-saved ratio is claimed; “faster” at most.

## README / submission wording

- README says Muse Image “preserves the rest of the artwork” — false for the raw plate;
  use “the composite only takes plate pixels inside the repainted coverage.”
- README/submission ranges are the ones above; no single-run cost claims.
- `docs/submission-final.md` limits section already matches; add the raw-plate sentence.
