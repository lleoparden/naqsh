"""Segmentation stage: turn Spark's boxes into pixel masks with SAM 3.1.

All regions go in one request: SAM accepts several box prompts under caller-chosen
object ids, so a three-region page costs one call ($0.0025), not three.

The mask raster is the size of the object's box, not the frame, so each mask is
pasted back at its box position.
"""

from __future__ import annotations

from typing import Any

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from .meta import SamObject, Usage, sam_segment
from .types import BBox, TextRegion


def build_box_prompt(boxes: list[BBox], width: int, height: int) -> str:
    """``<0f>1<|box;...|>,2<|box;...|>`` — the frame header and ids are required."""
    records = [
        f"{index + 1}<|box;x1={box.x1};y1={box.y1};x2={box.x2};y2={box.y2};w={width};h={height}|>"
        for index, box in enumerate(boxes)
    ]
    return "<0f>" + ",".join(records)


def _paste(mask: SamObject, size: tuple[int, int]) -> Image.Image:
    width, height = size
    raster = Image.frombytes("L", (mask.width, mask.height), bytes(255 if v else 0 for v in mask.raster))
    x1, y1, x2, y2, _fw, _fh = mask.box
    target_w, target_h = max(1, x2 - x1), max(1, y2 - y1)
    raster = raster.resize((target_w, target_h), Image.NEAREST)
    page = Image.new("L", (width, height), 0)
    page.paste(raster, (max(0, x1), max(0, y1)))
    return page


def segment_regions(
    image_png: bytes,
    regions: list[TextRegion],
    width: int,
    height: int,
    *,
    padding: int = 3,
) -> tuple[dict[str, Image.Image], Usage, list[str]]:
    """Returns region id -> full-page mask (L, 0/255), plus warnings."""
    warnings: list[str] = []
    if not regions:
        return {}, Usage(), ["no regions to segment"]

    boxes = [region.bbox.padded(padding, width, height) for region in regions]
    objects, usage = sam_segment(
        image_png,
        build_box_prompt(boxes, width, height),
        image_size=(width, height),
    )

    masks: dict[str, Image.Image] = {}
    by_id = {obj.object_id: obj for obj in objects}
    for index, region in enumerate(regions):
        obj = by_id.get(str(index + 1))
        if obj is None:
            warnings.append(f"{region.id}: SAM returned no mask; using its box")
            masks[region.id] = _box_mask(region.bbox, width, height, padding)
            continue
        mask = _paste(obj, (width, height))
        if mask.getbbox() is None:
            warnings.append(f"{region.id}: SAM mask was empty; using its box")
            mask = _box_mask(region.bbox, width, height, padding)
        masks[region.id] = mask
    return masks, usage, warnings


def _box_mask(box: BBox, width: int, height: int, padding: int) -> Image.Image:
    page = Image.new("L", (width, height), 0)
    page.paste(255, box.padded(padding, width, height).to_list())
    return page


def inner_box(mask: Image.Image, shrink_ratio: float = 0.12) -> BBox | None:
    """The rectangle inscribed in a mask after eroding it.

    A bubble's bounding box includes the tail and the widest part of an ellipse, so
    fitting to the bbox lets text spill over the outline. Eroding first approximates
    the usable interior.
    """
    bounds = mask.getbbox()
    if not bounds:
        return None
    width, height = bounds[2] - bounds[0], bounds[3] - bounds[1]
    kernel = max(3, int(min(width, height) * shrink_ratio))
    if kernel % 2 == 0:
        kernel += 1
    eroded = mask.filter(ImageFilter.MinFilter(kernel))
    inner = eroded.getbbox()
    if not inner or inner[2] - inner[0] < 12 or inner[3] - inner[1] < 12:
        return None
    return BBox(*inner)


def clean_flat_interior(
    image: Image.Image,
    mask: Image.Image,
    *,
    erode: int = 5,
    tolerance: float = 32.0,
    min_dominant: float = 0.6,
) -> tuple[Image.Image, bool]:
    """Flatten a balloon or caption interior that is already one flat colour.

    Inside a speech bubble the fill is a single colour, so any leftover ink (a ghost
    from an imperfect edit) is painted out with that colour. The mask is eroded first
    so the outline is never touched, and the operation is skipped when the interior is
    not dominated by one colour — a photograph must keep its texture.
    """
    interior = mask.filter(ImageFilter.MinFilter(2 * erode + 1)) if erode > 0 else mask
    selected = np.asarray(interior, dtype=np.uint8) > 127
    if selected.sum() < 500:
        return image, False

    canvas = np.asarray(image.convert("RGB"), dtype=np.uint8)
    values = canvas[selected].astype(np.int16)
    fill = np.median(values, axis=0)
    dominant = float((np.abs(values - fill).max(axis=1) <= tolerance).mean())
    if dominant < min_dominant:
        return image, False

    output = canvas.copy()
    output[selected] = fill.astype(np.uint8)
    return Image.fromarray(output, mode="RGB"), True


def dilate(mask: Image.Image, px: int) -> Image.Image:
    """Grow a mask so antialiased edges and the old lettering halo are covered."""
    if px <= 0:
        return mask
    return mask.filter(ImageFilter.MaxFilter(2 * px + 1))


def extend_with_box(mask: Image.Image, box: BBox, *, pad: int = 8) -> Image.Image:
    """Union a SAM mask with Spark's lettering box.

    SAM sometimes returns the bubble or only one line of a two-line block; the box
    is tight around the lettering by construction, so the union is what actually
    gets repainted. Cheap insurance against ghost lettering.
    """
    extended = mask.copy()
    ImageDraw.Draw(extended).rectangle(
        [max(0, box.x1 - pad), max(0, box.y1 - pad), box.x2 + pad, box.y2 + pad],
        fill=255,
    )
    return extended


def mask_array(mask: Image.Image) -> np.ndarray:
    return np.asarray(mask, dtype=np.uint8) > 127


def union(masks: list[Image.Image]) -> Image.Image:
    if not masks:
        raise ValueError("no masks")
    out = np.zeros((masks[0].height, masks[0].width), dtype=np.uint8)
    for mask in masks:
        out = np.maximum(out, np.asarray(mask, dtype=np.uint8))
    return Image.fromarray(out, mode="L")


def overlay_preview(base: Image.Image, masks: dict[str, Image.Image], color: tuple[int, int, int] = (214, 61, 67)) -> Image.Image:
    preview = base.convert("RGBA")
    tint = Image.new("RGBA", preview.size, (*color, 110))
    for mask in masks.values():
        preview.paste(tint, (0, 0), mask)
    return preview.convert("RGB")


def describe(objects: list[SamObject]) -> list[dict[str, Any]]:
    return [
        {
            "object_id": obj.object_id,
            "box": list(obj.box),
            "confidence": round(obj.confidence, 4),
            "mask": [obj.height, obj.width],
        }
        for obj in objects
    ]
