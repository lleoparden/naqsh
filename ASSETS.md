# Assets — sources and licenses

Rule for this project: only media we have the right to use. That means
Creative Commons (with the license recorded), public domain, or images generated
for this project with Muse Image. **No copyrighted comics, manga, or Webtoon
material is used, ever** — not even as a test image.

Every asset gets a row here *before* it is committed.

## Media

| Asset | Used for | Source | License | Added |
| --- | --- | --- | --- | --- |
| `assets/generated/test-panel.png` | API probes (Spark vision, SAM segmentation, Image edit) | Generated for this project with Muse Image (`muse-image-1.0`), prompt in `backend/scripts/smoke_image_generate.py` | Generated output, project-owned; Muse Image terms of use | 2026-10-27 |

## Fonts

| Font | Used for | Source | License |
| --- | --- | --- | --- |
| _none yet_ | Arabic typesetting candidates are evaluated in Phase 3 | — | — |

Candidate Arabic faces are all open-licensed (SIL OFL / Apache); each one is
added here with its license file before it ships.

## Notes

- Generated images are reproducible from the prompts recorded in
  `backend/scripts/`; the exact seed is not exposed by the API, so a rerun may
  differ slightly.
- If a CC0 photograph is used later, link the source page and quote the license
  line, not just the file name.
