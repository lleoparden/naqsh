"""Where does ghost lettering sit relative to the repaint coverage?

For a saved job folder, reconstruct the coverage used by the composite (SAM mask
unioned with Spark's reading box, then dilated), then classify remaining ink-like
pixels in the composite as inside or outside that coverage.

Usage: python backend/scripts/diagnose_plate.py <job-folder> [<job-folder> ...]
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

INK_TOLERANCE = 40.0
MIN_INK_LUMINANCE = 55.0


def _coverage(folder: Path, region: dict, size: tuple[int, int]) -> np.ndarray:
    mask = Image.open(folder / region["mask_path"]).convert("L")
    box = region["bbox"]
    draw = ImageDraw.Draw(mask)
    draw.rectangle([box[0] - 8, box[1] - 8, box[2] + 8, box[3] + 8], fill=255)
    grown = mask.filter(ImageFilter.MaxFilter(17))  # the composite's 8 px dilation
    return np.asarray(grown, dtype=np.uint8) > 127


def analyse(folder: Path) -> dict:
    job = json.loads((folder / "job.json").read_text(encoding="utf-8"))
    composite = Image.open(folder / "composite.png").convert("RGB")
    canvas = np.asarray(composite, dtype=np.int16)
    luminance = canvas @ np.array([0.299, 0.587, 0.114])

    rows = []
    inside_total = 0
    outside_total = 0
    overlay = composite.copy()
    draw = ImageDraw.Draw(overlay)
    for region in job["regions"]:
        x1, y1, x2, y2 = region["bbox"]
        pad = 40
        bx1, by1 = max(0, x1 - pad), max(0, y1 - pad)
        bx2, by2 = min(composite.width, x2 + pad), min(composite.height, y2 + pad)
        crop = canvas[by1:by2, bx1:bx2].reshape(-1, 3)
        fill = np.median(crop, axis=0)

        far = (np.abs(canvas - fill).max(axis=2) > INK_TOLERANCE) & (luminance > MIN_INK_LUMINANCE)
        area = np.zeros_like(far)
        area[by1:by2, bx1:bx2] = True
        coverage = _coverage(folder, region, composite.size)

        inside = far & area & coverage
        outside = far & area & ~coverage
        rows.append(
            {
                "region": region["id"],
                "reading_box": region["bbox"],
                "ink_inside_coverage": int(inside.sum()),
                "ink_outside_coverage": int(outside.sum()),
            }
        )
        inside_total += int(inside.sum())
        outside_total += int(outside.sum())

        # Mark outside-coverage ink in magenta on the overlay.
        ys, xs = np.nonzero(outside)
        for y, x in zip(ys[::3], xs[::3]):
            draw.point((int(x), int(y)), fill=(255, 0, 255))
        draw.rectangle(region["bbox"], outline=(0, 200, 0), width=2)

    overlay.save(folder / "diagnose-coverage.png")
    return {
        "job": folder.name,
        "regions": rows,
        "ink_inside_coverage": inside_total,
        "ink_outside_coverage": outside_total,
    }


def main() -> None:
    for arg in sys.argv[1:]:
        print(json.dumps(analyse(Path(arg)), indent=2))


if __name__ == "__main__":
    main()
