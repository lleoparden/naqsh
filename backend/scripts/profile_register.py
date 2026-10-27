"""Profile the register/composite stage on a stored job, offline and free.

Usage: python backend/scripts/profile_register.py [job-id]
"""

from __future__ import annotations

import cProfile
import io
import json
import pstats
import sys
import time
from contextlib import contextmanager
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PIL import Image  # noqa: E402

from app.pipeline import coverage as coverage_stage  # noqa: E402
from app.pipeline import plate as plate_stage  # noqa: E402
from app.pipeline import segment as segment_stage  # noqa: E402
from app.pipeline.job import JOBS_DIR, _compose, load_job  # noqa: E402
from app.pipeline.types import BBox  # noqa: E402

TIMES: dict[str, float] = {}


@contextmanager
def timed(name: str):
    started = time.perf_counter()
    yield
    TIMES[name] = TIMES.get(name, 0.0) + (time.perf_counter() - started)


def main() -> None:
    job_id = sys.argv[1] if len(sys.argv) > 1 else "e13f9585b24f"
    receipt = load_job(job_id)
    folder = JOBS_DIR / job_id
    source = Image.open(folder / "source.png").convert("RGB")
    plate_raw = Image.open(folder / "plate-raw.png").convert("RGB")

    regions = [r for r in receipt["regions"] if r.get("action", "translate") not in ("skip", "optional")]
    boxes = [BBox(*r["bbox"]) for r in regions]
    masks = []
    for region in regions:
        with Image.open(folder / f"mask-{region['id']}.png") as mask:
            masks.append(mask.convert("L"))
    print(f"{job_id}: {len(regions)} repaint regions, {source.size}")

    coverage = []
    with timed("coverage_for (all regions)"):
        for region, mask in zip(regions, masks):
            cov, _area = coverage_stage.coverage_for(source, mask, BBox(*region["bbox"]))
            coverage.append(cov)

    with timed("estimate_shift.total"):
        with timed("estimate_shift.edges"):
            edges_source = plate_stage._edges(source)
            edges_plate = plate_stage._edges(plate_raw.resize(source.size, Image.LANCZOS))
        with timed("estimate_shift.phase"):
            plate_stage._phase_shift(edges_source, edges_plate)
        with timed("estimate_shift.local_search"):
            dx, dy = plate_stage.estimate_shift(source, plate_raw, boxes)
    print("shift", dx, dy)

    with timed("apply_shift"):
        aligned = plate_stage.apply_shift(plate_raw, source.size, dx, dy)

    with timed("composite (mask union + blend)"):
        composite_img, stats = plate_stage.composite(source, aligned, coverage)

    flat_cleaned = 0
    with timed("clean_flat_interior (per mask)"):
        for mask in coverage:
            composite_img, changed = segment_stage.clean_flat_interior(composite_img, mask)
            flat_cleaned += int(changed)

    with timed("alignment_report (ring per region)"):
        plate_stage.alignment_report(source, aligned, coverage)

    with timed("measure_dirty_plate"):
        plate_stage.measure_dirty_plate(aligned, boxes)

    total = sum(TIMES.values())
    print("\nstep timings (ms):")
    for name, seconds in sorted(TIMES.items(), key=lambda item: -item[1]):
        print(f"  {name:42s} {seconds * 1000:9.1f}")
    print(f"  {'SUM':42s} {total * 1000:9.1f}")

    profile = cProfile.Profile()
    profile.enable()
    plate_stage.estimate_shift(source, plate_raw, boxes)
    plate_stage.apply_shift(plate_raw, source.size, dx, dy)
    plate_stage.composite(source, aligned, coverage)
    plate_stage.alignment_report(source, aligned, coverage)
    profile.disable()
    stream = io.StringIO()
    pstats.Stats(profile, stream=stream).sort_stats("cumulative").print_stats(18)
    print(stream.getvalue())


if __name__ == "__main__":
    main()
