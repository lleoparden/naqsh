"""Render stage: draw the fitted Arabic layers over the cleaned plate.

Lines are stacked by their measured ink boxes, not by the em size, so a descender
or a final kaf cannot be clipped by the region's edge.
"""

from __future__ import annotations

from PIL import Image, ImageDraw

from .typeset import LINE_GAP_RATIO, _font
from .types import Layout, TextRegion


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
    draw = ImageDraw.Draw(canvas)

    for region in regions:
        layout = layouts.get(region.id)
        if layout is None or not layout.lines:
            continue
        font = _font(region.font_family, layout.size)
        color = (color_of or {}).get(region.id, region.color)
        bbox = region.container or region.bbox
        center_x = (bbox.x1 + bbox.x2) / 2

        measured = [(line, draw.textbbox((0, 0), line, font=font)) for line in layout.lines]
        gap = int(round(layout.size * LINE_GAP_RATIO))
        heights = [box[3] - box[1] for _line, box in measured]
        block_height = sum(heights) + gap * max(0, len(measured) - 1)
        top = (bbox.y1 + bbox.y2) / 2 - block_height / 2

        for (line, box), line_height in zip(measured, heights, strict=True):
            line_width = box[2] - box[0]
            x = center_x - line_width / 2 - box[0]
            y = top - box[1]
            draw.text((x, y), line, font=font, fill=(*color, 255))
            top += line_height + gap

    return canvas.convert("RGB")
