# Demo sources v3 — plate diff clarification (0)

The v2 report’s “plate diff outside masks 2.49–7.38” measured:

- **Images:** for each v2 live job, `source.png` vs **`plate.png`** — the registered Muse
  Image repaint, before masking — at 1280×1920 RGB, values 0–255.
- **Pixels:** every pixel **outside the union of the saved `mask-*.png`** (raw SAM masks,
  not the dilated coverage and not the text boxes). Mean absolute RGB difference.
- **Background layers:** ON for those runs, but this metric does not involve them. It
  compares the raw plate, which is a full-page re-render and legitimately differs
  everywhere. **The number is expected to be non-zero.**
- **Earlier “max diff 0”:** that measured `source.png` vs **`composite.png`** outside the
  **repaint coverage** (mask ∪ ink extent ∪ reading box, dilated) — the only pixels the
  pipeline may replace. That remains true: outside coverage the composite is byte-for-byte
  the original.
- **With background layers ON**, the scene/bubble layers are cut from that composite; they
  do not change outside-coverage pixels. They only expose or cover regions inside it.

**Plain statement:** “everything outside the text regions stays the original pixels” is
still true for the **composite/export outside repaint coverage**. It is **not** a claim
about the raw plate, which is re-rendered everywhere; the v2 metric measured the plate.
