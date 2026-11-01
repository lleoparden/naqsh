# Mascot expression variants (exploration)

Three concepts — **dot-a**, **ink-a**, **layers** — were chosen for expression tests because
they are the most distinct categories (dot, ink drop, stacked sheets). This is not a final
design choice.

Nine Muse Image edits (3 states × 3 concepts) live at
`L:\naqsh-review\mascot\expressions\`; prompts and costs are in
`docs/mascot-manifest.json`. Cost **\.09**.

## Consistency, honestly

- **dot-a:** shape, silhouette, palette and background stay consistent; idle/thinking/
  happy differ only in the face. Thinking dots are very faint.
- **ink-a:** shape, highlight and rim stay consistent; expressions read; thinking dots are
  visible above the drop.
- **layers:** the silhouette shifts between states (top sheet angle/offset) and the face
  moves slightly; still recognizable, but the least consistent of the three. Frame-to-frame
  identity is not reliable enough to promise a seamless animation without hand redrawing.

No frame interpolation or SVG yet; these are raster explorations.
