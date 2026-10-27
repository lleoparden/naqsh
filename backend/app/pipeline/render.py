"""Render: draw the fitted, shaped Arabic over the cleaned plate."""

from __future__ import annotations

from PIL import Image, ImageDraw

from .shaping import draw_line, shape_line
from .types import Layout, TextRegion

LINE_GAP_RATIO = 0.20


def contrast_color(original: Image.Image, region: TextRegion) -> tuple[int, int, int]:
    """Keep the original lettering colour when it has contrast, else fall back to ink."""
    bbox = region.bbox
    crop = original.crop((bbox.x1, bbox.y1, bbox.x2, bbox.y2)).convert("L")
    pixels = list(crop.getdata())
    if not pixels:
        return region.color
    darkest = sorted(pixels)[: max(1, len(pixels) // 20)]
    mean_dark = sum(darkest) / len(darkest)
    lightest = sorted(pixels)[-max(1, len(pixels) // 20) :]
    mean_light = sum(lightest) / len(lightest)
    if mean_light - mean_dark < 40:
        return (20, 17, 15)
    return region.color


def draw_regions(
    base: Image.Image,
    regions: list[TextRegion],
    layouts: dict[str, Layout],
    *,
    color_of: dict[str, tuple[int, int, int]] | None = None,
) -> Image.Image:
    canvas = base.convert("RGBA")
    for region in regions:
        layout = layouts.get(region.id)
        if layout is None or not layout.lines:
            continue
        # Policy: skipped regions keep the original artwork; optional regions (SFX)
        # stay off by default until the editor turns them on. Prices keep their
        # original Latin numerals and are drawn from source_text by the caller.
        if region.action in ("skip", "optional"):
            continue
        family = region.font_family
        color = (color_of or {}).get(region.id, region.color)
        box = region.container or region.bbox
        center_x = (box.x1 + box.x2) / 2

        shaped = [shape_line(line, family, layout.size) for line in layout.lines]
        gap = int(round(layout.size * LINE_GAP_RATIO))
        block = sum(line.ink_height for line in shaped) + gap * max(0, len(shaped) - 1)
        top = (box.y1 + box.y2) / 2 - block / 2
        for line in shaped:
            draw_line(canvas, line, family, center_x=center_x, top=top, color=color)
            top += line.ink_height + gap

    return canvas.convert("RGB")
