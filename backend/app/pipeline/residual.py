"""Residual-text detection and per-region repair strategies.

Order of preference (Muse Image stays the default for textured art):

1. the Muse Image plate (after registration and masked compositing);
2. one Muse Image retry when a region still shows lettering;
3. a flat-interior fill for regions whose background is one colour;
4. OpenCV Telea inpainting for textured regions that still fail.

The detector is Muse Spark looking at 100% crops of the region, not a pixel
heuristic: dirty_ratio overlapped between clean and ghosted plates and could not
be thresholded.
"""

from __future__ import annotations

import io
from dataclasses import dataclass
from typing import Any

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from .meta import Usage, spark_json
from .types import BBox

PROMPT = """These are {count} crops from one page of a comic/poster/menu, at 100% zoom, each labelled with an id ({ids}). The crops include generous margins, so a word may sit above or beside the area that used to hold it.

Question for each crop: is any original lettering, letter fragment or ghost text still visible anywhere in the crop? Ignore the artwork itself (characters, food, buildings, paper texture, lines); only report text-like marks. A clean empty speech bubble or caption box is NOT residual text. A faint, partly erased, smeared or blurry word still counts as residual. Price digits alone also count.

Return strict JSON only:
{{"regions": [{{"id": "t1", "residual": true, "note": "faint MORNING at the bottom"}}]}}
Use residual=false and a short note when the crop is clean."""


@dataclass
class ResidualVerdict:
    region_id: str
    residual: bool
    note: str


def crop_region(image: Image.Image, box: BBox, pad: int = 48, max_width: int = 760) -> Image.Image:
    x1 = max(0, box.x1 - pad)
    y1 = max(0, box.y1 - pad)
    x2 = min(image.width, box.x2 + pad)
    y2 = min(image.height, box.y2 + pad)
    crop = image.crop((x1, y1, x2, y2))
    if crop.width > max_width:
        ratio = max_width / crop.width
        crop = crop.resize((max_width, max(32, int(crop.height * ratio))), Image.LANCZOS)
    return crop


def build_montage(image: Image.Image, boxes: dict[str, BBox], pad: int = 48) -> Image.Image:
    """One labelled image so the whole page costs one vision call, not one per region."""
    crops = [(region_id, crop_region(image, box, pad)) for region_id, box in boxes.items()]
    width = max(c.width for _id, c in crops)
    label_height = 26
    height = sum(c.height + label_height + 8 for _id, c in crops)
    sheet = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(sheet)
    y = 0
    for region_id, crop in crops:
        draw.rectangle([0, y, width, y + label_height], fill=(242, 238, 228))
        draw.text((8, y + 6), f"{region_id}  ({crop.width}x{crop.height})", fill=(20, 17, 15))
        sheet.paste(crop, (0, y + label_height))
        y += crop.height + label_height + 8
    return sheet


def detect_residual(image: Image.Image, boxes: dict[str, BBox]) -> tuple[list[ResidualVerdict], Usage, str]:
    montage = build_montage(image, boxes)
    buffer = io.BytesIO()
    montage.save(buffer, format="PNG")
    prompt = PROMPT.format(count=len(boxes), ids=", ".join(boxes))
    payload, usage, raw = spark_json(buffer.getvalue(), prompt, max_output_tokens=1200)
    verdicts: list[ResidualVerdict] = []
    for item in payload.get("regions") or []:
        if not isinstance(item, dict):
            continue
        verdicts.append(
            ResidualVerdict(
                region_id=str(item.get("id") or ""),
                residual=bool(item.get("residual")),
                note=str(item.get("note") or ""),
            )
        )
    return verdicts, usage, raw


def flat_fill(image: Image.Image, mask: Image.Image, coverage: Image.Image) -> tuple[Image.Image, bool]:
    """Repaint a flat region with the colour just inside its outline.

    The fill colour comes from a band inside the mask boundary (the ghost strokes sit
    in the middle), and only pixels that differ from it are replaced, so a drawing
    that touches the region keeps its edges. Skipped when the band is not dominated by
    one colour — that is a textured region and a flat fill would be a lie.
    """
    # Sample a band inside the outline (8–20 px in): the ghost sits in the middle and
    # the black outline would skew a boundary sample.
    inner = np.asarray(mask.filter(ImageFilter.MinFilter(17)), dtype=np.uint8) > 127
    deeper = np.asarray(mask.filter(ImageFilter.MinFilter(41)), dtype=np.uint8) > 127
    band = inner & ~deeper
    canvas = np.asarray(image.convert("RGB"), dtype=np.uint8)
    values = canvas[band]
    if values.size < 300:
        return image, False
    fill = np.median(values.astype(np.int16), axis=0)
    dominant = float((np.abs(values.astype(np.int16) - fill).max(axis=1) <= 40).mean())
    if dominant < 0.55:
        return image, False

    area = np.asarray(coverage, dtype=np.uint8) > 127
    pixels = canvas.astype(np.int16)
    far = np.abs(pixels - fill).max(axis=2) > 38
    luminance = pixels @ np.array([0.299, 0.587, 0.114])
    keep_outline = luminance < 45
    target = area & far & ~keep_outline
    if int(target.sum()) < 20:
        return image, False
    output = canvas.copy()
    output[target] = fill.astype(np.uint8)
    return Image.fromarray(output, mode="RGB"), True


def inpaint_region(image: Image.Image, coverage: Image.Image) -> Image.Image:
    """Last resort for textured art: Telea inpainting inside the repaint area."""
    canvas = np.asarray(image.convert("RGB"), dtype=np.uint8)
    mask = (np.asarray(coverage, dtype=np.uint8) > 127).astype(np.uint8) * 255
    if int(mask.sum()) == 0:
        return image
    repaired = cv2.inpaint(cv2.cvtColor(canvas, cv2.COLOR_RGB2BGR), mask, 3, cv2.INPAINT_TELEA)
    return Image.fromarray(cv2.cvtColor(repaired, cv2.COLOR_BGR2RGB))


def region_is_flat(image: Image.Image, mask: Image.Image, max_std: float = 34.0) -> bool:
    interior = np.asarray(mask.filter(ImageFilter.MinFilter(13)), dtype=np.uint8) > 127
    if interior.sum() < 300:
        return False
    values = np.asarray(image.convert("RGB"), dtype=np.int16)[interior]
    return bool(values.std(axis=0).max() <= max_std)


def summarise(verdicts: list[ResidualVerdict]) -> dict[str, Any]:
    return {
        "checked": len(verdicts),
        "residual": [v.region_id for v in verdicts if v.residual],
        "notes": {v.region_id: v.note for v in verdicts if v.note},
    }
