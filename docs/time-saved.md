# Time saved — measurement sheet (archived)

**Archived 2026-10-29:** the owner is not an editor, so a manual baseline would not be
honest. **No time-saved ratio is claimed**; the only allowed wording is “faster”. The
Naqsh numbers below remain as historical context, and the manual column stays empty.


Status: **baseline column is empty.** The ratio is not computed until the owner's timed
manual run exists. No estimated number appears in this file.

## What Naqsh measured (live runs, DEMO_MODE=0)

Source: `docs/evidence/phase-7/live-runs.json`, six live API runs (comic ×3, menu ×3)
on 2026-10-27. "Wall" is the HTTP round trip; "total" is the receipt's own sum of
stages. Both are real numbers from the receipts, not estimates.

| Page | Runs | Wall median (range) | Receipt total median (range) | Cost median (range) |
|---|---|---|---|---|
| `assets/generated/fixtures/01-comic-flat.png` (1280×1920) | 3 | 57.6 s (1 of 3 measured) | **54.5 s** (53.1–57.2) | **$0.0263** (0.0254–0.0286) |
| `assets/generated/fixtures/03-menu-paper.png` (1280×1920) | 3 | 189.0 s (1 of 3 measured) | **181.1 s** (162.1–206.8) | **$0.0502** (0.0442–0.0676) |

Per-stage medians and ranges are in the evidence JSON and summarised in
`docs/submission-notes.md`.

## What the manual baseline must measure

Same page files, same definition of done, one timed run each (or one page if time is
short — say which). Fill this table by hand:

| Page | Tool(s) used | Date | Manual minutes | Output saved (layered file) |
|---|---|---|---|---|
| `01-comic-flat.png` | _e.g. Photoshop / Illustrator / Photopea_ | | | |
| `03-menu-paper.png` | | | | |

**"Done" means**, for the page being timed:

1. Every piece of lettering is replaced with Arabic (no English left).
2. Arabic is set right-to-left with correct joining, in a size that fits the original
   space.
3. The background behind the old lettering is cleaned (no ghost text, no smear).
4. A layered file is saved with text still editable, plus a flat PNG.

Stop the clock when the file is saved. Do not count writing the report or exporting
the video.

## Ratio (only when both sides exist)

```
ratio = manual_minutes / naqsh_minutes
```

`naqsh_minutes = receipt total median / 60` for the same page.

| Page | Naqsh minutes | Manual minutes | Ratio |
|---|---|---|---|
| comic | 0.91 (54.5 s) | _empty_ | **not computed — baseline empty** |
| menu | 3.02 (181.1 s) | _empty_ | **not computed — baseline empty** |

Rules:

- One ratio per page, computed from the medians shown here, not from a single best run.
- If the owner only times one page, the comic is the one to time: it is the simplest
  to compare and the least flattering to Naqsh (few regions).
- Any claim in the video or submission must quote the ratio and the page, and say the
  baseline was measured by the author with a stopwatch.
