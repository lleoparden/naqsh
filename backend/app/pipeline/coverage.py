"""Coverage built from the actual ink on the page, not from guessed boxes.

The failure diagnosis showed residual lettering sitting outside both the SAM mask
and Spark's reading box: the original lettering was taller than either. So the
repaint area is grown to the real ink extent: pixels near the region that are not
the local fill and not the black outline.
"""

from __future__ import annotations

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from . import morph

from .types import BBox

MIN_INK_LUMINANCE = 55.0
INK_TOLERANCE = 45.0


def ink_extent(
    source: Image.Image,
    mask: Image.Image,
    reading_box: BBox,
    *,
    search_pad: int | None = None,
    search_pad_x: int | None = None,
    search_pad_y: int | None = None,
    fill_tolerance: float = INK_TOLERANCE,
) -> BBox | None:
    """Bounding box of lettering-like pixels around a region, or None."""
    canvas = np.asarray(source.convert("RGB"), dtype=np.int16)
    luminance = canvas @ np.array([0.299, 0.587, 0.114])

    interior = np.asarray(mask.filter(ImageFilter.MinFilter(9)), dtype=np.uint8) > 127
    if interior.sum() < 200:
        return None
    fill = np.median(canvas[interior], axis=0)

    # Spark's boxes can be much shorter than the lettering (a display line whose
    # ascenders sit above the box), so search a generous margin around it.
    if search_pad is not None:
        pad_x = pad_y = search_pad
    else:
        pad_x = 8 if search_pad_x is None else search_pad_x
        pad_y = max(72, int(0.6 * max(reading_box.width, reading_box.height))) if search_pad_y is None else search_pad_y
    x1 = max(0, reading_box.x1 - pad_x)
    y1 = max(0, reading_box.y1 - pad_y)
    x2 = min(source.width, reading_box.x2 + pad_x)
    y2 = min(source.height, reading_box.y2 + pad_y)

    crop = canvas[y1:y2, x1:x2]
    crop_luminance = luminance[y1:y2, x1:x2]
    ink = (np.abs(crop - fill).max(axis=2) > fill_tolerance) & (crop_luminance > MIN_INK_LUMINANCE)
    if int(ink.sum()) < 30:
        return None

    ys, xs = np.nonzero(ink)
    return BBox(
        max(0, x1 + int(xs.min()) - 6),
        max(0, y1 + int(ys.min()) - 6),
        min(source.width, x1 + int(xs.max()) + 6),
        min(source.height, y1 + int(ys.max()) + 6),
    )


def coverage_for(
    source: Image.Image,
    mask: Image.Image,
    reading_box: BBox,
    *,
    dilate_px: int = 10,
) -> tuple[Image.Image, BBox]:
    """Mask ∪ nearby ink, dilated for antialiased edges.

    The ink search is anchored to the SAM mask, not to Spark's reading box, and only
    grows the mask by a few pixels horizontally. Vertically it searches further: large
    descenders (e.g. the bottom of "MORNING") can sit 40+ px below the mask, and leaving
    them outside the coverage leaves letter fragments in the output.
    """
    mask_bbox = mask.getbbox()
    base = BBox(*mask_bbox) if mask_bbox else reading_box
    extent = ink_extent(source, mask, base, search_pad_x=8, search_pad_y=40)
    area = base
    if extent is not None:
        area = BBox(
            min(base.x1, extent.x1),
            min(base.y1, extent.y1),
            max(base.x2, extent.x2),
            max(base.y2, extent.y2),
        )

    coverage = mask.copy()
    ImageDraw.Draw(coverage).rectangle(area.to_list(), fill=255)
    if dilate_px > 0:
        coverage = morph.dilate(coverage, dilate_px)
    return coverage, area
