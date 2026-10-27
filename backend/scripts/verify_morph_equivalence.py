"""Prove the fast morphology changed no pixels on stored jobs.

Rebuilds the real job path: coverage_for per region, then the composite that unions
those coverage masks and blends the plate. Reference uses Pillow MaxFilter everywhere;
fast uses cv2 morphology. Reports max pixel diff and differing pixel count.

Usage: python backend/scripts/verify_morph_equivalence.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.pipeline import coverage as coverage_stage  # noqa: E402
from app.pipeline import morph, plate as plate_stage, segment as segment_stage  # noqa: E402
from app.pipeline.job import JOBS_DIR, load_job  # noqa: E402
from app.pipeline.types import BBox  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
JOBS = ["e13f9585b24f", "d3dbface16b8", "605213b894ff"]


def old_coverage_for(source: Image.Image, mask: Image.Image, reading_box: BBox, *, dilate_px: int = 10) -> Image.Image:
    extent = coverage_stage.ink_extent(source, mask, reading_box)
    area = reading_box
    if extent is not None:
        area = BBox(
            min(reading_box.x1, extent.x1),
            min(reading_box.y1, extent.y1),
            max(reading_box.x2, extent.x2),
            max(reading_box.y2, extent.y2),
        )
    coverage = mask.copy()
    ImageDraw.Draw(coverage).rectangle(area.to_list(), fill=255)
    return coverage.filter(ImageFilter.MaxFilter(2 * dilate_px + 1))


def old_composite(source: Image.Image, plate: Image.Image, masks: list[Image.Image], dilation: int = 8) -> Image.Image:
    coverage = np.zeros((source.height, source.width), dtype=np.uint8)
    for mask in masks:
        coverage = np.maximum(coverage, np.asarray(mask.filter(ImageFilter.MaxFilter(2 * dilation + 1)), dtype=np.uint8))
    inside = coverage > 127
    original = np.asarray(source.convert("RGB"), dtype=np.uint8)
    replacement = np.asarray(plate.convert("RGB"), dtype=np.uint8)
    output = original.copy()
    output[inside] = replacement[inside]
    return Image.fromarray(output, mode="RGB")


def main() -> None:
    rows = []
    for job_id in JOBS:
        receipt = load_job(job_id)
        folder = JOBS_DIR / job_id
        source = Image.open(folder / "source.png").convert("RGB")
        raw = Image.open(folder / "plate-raw.png").convert("RGB")
        regions = [r for r in receipt["regions"] if r.get("action", "translate") not in ("skip", "optional")]
        masks = []
        boxes = []
        for region in regions:
            with Image.open(folder / f"mask-{region['id']}.png") as mask:
                masks.append(mask.convert("L"))
            boxes.append(BBox(*region["bbox"]))
        dx, dy = plate_stage.estimate_shift(source, raw, boxes)
        aligned = plate_stage.apply_shift(raw, source.size, dx, dy)

        old_covs = [old_coverage_for(source, mask, box) for mask, box in zip(masks, boxes)]
        new_covs = [coverage_stage.coverage_for(source, mask, box)[0] for mask, box in zip(masks, boxes)]
        cov_diffs = [
            (int(np.abs(np.asarray(a, dtype=np.int16) - np.asarray(b, dtype=np.int16)).max()),
             int((np.asarray(a) != np.asarray(b)).sum()))
            for a, b in zip(old_covs, new_covs)
        ]

        reference = np.asarray(old_composite(source, aligned, old_covs), dtype=np.int16)
        fast, _stats = plate_stage.composite(source, aligned, new_covs)
        fast_arr = np.asarray(fast, dtype=np.int16)
        diff = np.abs(reference - fast_arr)

        row = {
            "job": job_id,
            "regions": len(regions),
            "shift": [dx, dy],
            "composite_max_abs_diff": int(diff.max()),
            "composite_differing_pixels": int((diff > 0).sum()),
            "coverage_max_abs_diff": max(item[0] for item in cov_diffs),
            "coverage_differing_pixels": sum(item[1] for item in cov_diffs),
        }
        rows.append(row)
        print(json.dumps(row))

    out = REPO / "docs" / "evidence" / "phase-8" / "morph-equivalence.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rows, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
