# Decisions

Expensive-to-reverse choices, dated. If a decision is revisited, add a new entry
rather than editing the old one.

## 2026-10-27 — Repository and workflow

- **New repository, new code.** No code or asset from the author's earlier desktop
  design tool is reused. Workflow conventions (branching, Conventional Commits,
  epic/sub-issue tracking, self-reviewed PRs, agent instruction files) are
  re-created fresh for Naqsh.
- **Public repo from the first commit**, with `.env` gitignored and
  `.env.example` committed. The key never enters the repository or a log.

## 2026-10-27 — Model roles

- **SAM 3.1 produces layer geometry**, not a text detector bolted onto a VLM. It
  gives pixel masks with stable ids, which the fitter needs.
- **Muse Spark is the text engine**: read, translate, and style-classify in one
  vision call, returning per-region JSON. One model doing all three keeps the
  translation aware of the space it must fit.
- **Muse Image paints the clean plate.** Accepted only for the *inside* of text
  regions; the composite is masked, so drift outside the mask cannot damage the
  page.

## 2026-10-27 — Inpainting strategy (Plan A / B / C)

Muse Image exposes no mask parameter (multipart `mask` → 400
`unsupported_parameter`), and instruction edits do not guarantee geometry. So:

- **A.** Instruction edit for the whole page, then composite **only inside** the
  SAM text masks. Outside the masks the original pixels win.
- **B.** If the edit drifts or looks wrong, classical inpainting (OpenCV
  Telea/NS) from the SAM mask, seeded with the region's sampled fill colour.
- **C.** Always-available fallback: an opaque vector shape (bubble interior)
  above the original art, so ghost lettering is hidden by composition rather than
  repair. This is a legitimate lettering technique, not a hack.

## 2026-10-27 — Export contract

- Layered export is **SVG with real `<text>` elements** (editable in Illustrator,
  Inkscape, Figma) plus a flat PNG. Text is not outlined; outlines are an option
  only if a font cannot be embedded, because outlined text is not editable and the
  product promise is editability.

## 2026-10-27 — Vertical slice first

The pipeline is assembled end to end on one page as early as possible (Phase 2),
then each risky stage is hardened behind a gate. Rationale: the demo video is 25%
of the score and must show the full pipeline; a beautiful stage that never meets
the others is worthless.
