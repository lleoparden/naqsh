"""Does the "after" composite match the original outside the text regions?

Reconstructs the repaint coverage exactly as the pipeline does (mask ∪ ink extent ∪
reading box, dilated, plus menu leader boxes) and compares source.png with
composite.png outside it. Outside coverage the composite copies the original, so this
must be pixel-identical; a nonzero result would mean the after side is the raw plate or
is offset.

Usage: python backend/scripts/measure_after_alignment.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.pipeline import coverage as coverage_stage  # noqa: E402
from app.pipeline import morph  # noqa: E402
from app.pipeline.job import JOBS_DIR, load_job  # noqa: E402
from app.pipeline.types import BBox  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
JOBS = ["d3dbface16b8", "e13f9585b24f", "6a8aa7a0829b"]


def main() -> None:
    rows = []
    for job_id in JOBS:
        receipt = load_job(job_id)
        folder = JOBS_DIR / job_id
        source_image = Image.open(folder / "source.png").convert("RGB")
        source = np.asarray(source_image, dtype=np.int16)
        after = np.asarray(Image.open(folder / "composite.png").convert("RGB"), dtype=np.int16)

        coverage = Image.new("L", source_image.size, 0)
        painter = ImageDraw.Draw(coverage)
        for region in receipt["regions"]:
            if region.get("action", "translate") in ("skip", "optional"):
                continue
            mask_path = folder / f"mask-{region['id']}.png"
            if not mask_path.is_file():
                continue
            mask = Image.open(mask_path).convert("L")
            cov, _area = coverage_stage.coverage_for(source_image, mask, BBox(*region["bbox"]))
            coverage = Image.fromarray(np.maximum(np.asarray(coverage, dtype=np.uint8), np.asarray(cov, dtype=np.uint8)))
        # Menu leader boxes were painted into coverage at segment time; add them back.
        segment = next((stage for stage in receipt["stages"] if stage.get("name") == "segment"), {})
        for leader in segment.get("leaders") or []:
            painter = ImageDraw.Draw(coverage)
            painter.rectangle(leader["bbox"], fill=255)

        inside = np.asarray(morph.dilate(coverage, 8), dtype=np.uint8) > 127
        outside = ~inside
        diff = np.abs(source - after).max(axis=2)
        values = diff[outside]
        row = {
            "job": job_id,
            "size": [int(source.shape[1]), int(source.shape[0])],
            "outside_pixels": int(outside.sum()),
            "outside_max_abs_diff": int(values.max()) if values.size else 0,
            "outside_mean_abs_diff": round(float(values.mean()), 4) if values.size else 0.0,
            "outside_differing_pixels": int((values > 0).sum()),
            "outside_over_8_pixels": int((values > 8).sum()),
            "border_top_left_max": int(diff[0:140, 0:220].max()),
        }
        rows.append(row)
        print(json.dumps(row))

    out = REPO / "docs" / "evidence" / "ui" / "after-alignment.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rows, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
