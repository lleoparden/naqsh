"""Three live menu runs: leader-dot removal, before/after crops per line.

Usage:
  python backend/scripts/run_leader_check.py            # runs the pages
  python backend/scripts/run_leader_check.py --sheet-only
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.pipeline.job import JOBS_DIR, run_page_job  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
PAGE = REPO / "assets" / "generated" / "fixtures" / "03-menu-paper.png"
EVIDENCE = REPO / "docs" / "evidence" / "phase-5"
MAX_REGIONS = 4


def build_sheet(runs: list[dict]) -> Path:
    cells = []
    for run in runs:
        folder = JOBS_DIR / run["job"]
        receipt = json.loads((folder / "job.json").read_text(encoding="utf-8"))
        by_id = {r["id"]: r for r in receipt["regions"]}
        picked = [entry["region"] for entry in run["leaders"]][:MAX_REGIONS]
        if not picked:
            picked = [r["id"] for r in receipt["regions"][:MAX_REGIONS]]
        row = []
        for region_id in picked:
            region = by_id.get(region_id)
            if region is None:
                continue
            x1, y1, x2, y2 = region["bbox"]
            box = (
                max(0, x1 - 26),
                max(0, y1 - 18),
                min(receipt["width"], x2 + 26),
                min(receipt["height"], y2 + 18),
            )
            before = Image.open(folder / "source.png").convert("RGB").crop(box)
            after = Image.open(folder / "output.png").convert("RGB").crop(box)
            row.append((region_id, before, after))
        cells.append((run, row))

    cell_w = max(max(b.width, a.width) for _r, row in cells for _i, b, a in row) + 12
    cell_h = max(max(b.height, a.height) for _r, row in cells for _i, b, a in row) * 2 + 46
    width = cell_w * MAX_REGIONS
    sheet = Image.new("RGB", (width, cell_h * len(cells)), "white")
    draw = ImageDraw.Draw(sheet)
    for row_index, (run, row) in enumerate(cells):
        y = row_index * cell_h
        draw.text((6, y + 4), f"run{run['run']} {run['job']} — top: before, bottom: after", fill=(20, 20, 20))
        for column, (region_id, before, after) in enumerate(row):
            x = column * cell_w
            draw.text((x + 6, y + 20), region_id, fill=(90, 90, 90))
            sheet.paste(before, (x, y + 32))
            sheet.paste(after, (x, y + 32 + before.height + 4))
    path = EVIDENCE / "leader-dots-before-after.png"
    sheet.save(path)
    return path


def main() -> None:
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    if "--sheet-only" in sys.argv:
        runs = json.loads((EVIDENCE / "leader-dots-runs.json").read_text(encoding="utf-8"))
        print(build_sheet(runs))
        return

    runs = []
    for index in range(1, 4):
        job = run_page_job(PAGE.read_bytes(), "egyptian")
        receipt = json.loads((JOBS_DIR / job.id / "job.json").read_text(encoding="utf-8"))
        segment = next(s for s in receipt["stages"] if s["name"] == "segment")
        leaders = segment.get("leaders") or []
        runs.append({"run": index, "job": job.id, "leaders": leaders, "cost": receipt["total_cost_usd"]})
        print(f"run{index}: {job.id} leaders={[(l['region'], l['dots']) for l in leaders]}", flush=True)

    (EVIDENCE / "leader-dots-runs.json").write_text(json.dumps(runs, indent=2), encoding="utf-8")
    print(build_sheet(runs))


if __name__ == "__main__":
    main()
