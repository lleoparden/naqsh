"""Phase 4 gate: run every fixture page twice and build one contact sheet.

Each run does the full pipeline (read, segment, plate, register, verify, route,
final check). The sheet shows 100%-zoom crops of every text region after cleaning,
labelled page / run / region / strategy, so a human can judge ghost lettering and
smears directly.

Usage: python backend/scripts/run_gate.py [--runs 2] [--pages 5]
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.pipeline.job import JOBS_DIR, run_page_job  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
FIXTURES = sorted((REPO / "assets" / "generated" / "fixtures").glob("*.png"))
EVIDENCE = REPO / "docs" / "evidence" / "phase-4"


def crop_cell(image: Image.Image, bbox: list[int], pad: int = 26, max_w: int = 260, max_h: int = 160) -> Image.Image:
    x1, y1, x2, y2 = bbox
    crop = image.crop(
        (
            max(0, x1 - pad),
            max(0, y1 - pad),
            min(image.width, x2 + pad),
            min(image.height, y2 + pad),
        )
    )
    ratio = min(max_w / crop.width, max_h / crop.height)
    if ratio < 1:
        crop = crop.resize((max(1, int(crop.width * ratio)), max(1, int(crop.height * ratio))), Image.LANCZOS)
    return crop


def build_sheet(runs: list[dict]) -> Path:
    cell_w, cell_h, label_h, gap = 272, 190, 18, 8
    columns = max(len(run["regions"]) for run in runs)
    width = columns * (cell_w + gap) + gap
    height = len(runs) * (cell_h + label_h + gap) + gap + 34
    sheet = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(sheet)
    draw.text((gap, 8), "Phase 4 clean-plate gate - 100% crops of each text region after cleaning", fill=(0, 0, 0))

    for row, run in enumerate(runs):
        y = 34 + gap + row * (cell_h + label_h + gap)
        output = Image.open(JOBS_DIR / run["job"] / "output.png").convert("RGB")
        draw.text(
            (gap, y),
            f"{run['page']} run{run['run']} | {run['cost']:.4f} USD | {run['ms'] / 1000:.0f}s | final residual: {run['final_residual'] or 'none'}",
            fill=(60, 60, 60),
        )
        for column, region in enumerate(run["regions"]):
            x = gap + column * (cell_w + gap)
            cell = crop_cell(output, region["bbox"])
            sheet.paste(cell, (x, y + label_h))
            draw.rectangle([x - 1, y + label_h - 1, x + cell.width, y + label_h + cell.height], outline=(200, 200, 200))
            draw.text((x, y + 4), f"{region['id']} {region['strategy']}", fill=(20, 20, 20))
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    path = EVIDENCE / "contact-sheet.png"
    sheet.save(path)
    return path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=int, default=2)
    parser.add_argument("--pages", type=int, default=5)
    args = parser.parse_args()

    pages = FIXTURES[: args.pages]
    runs: list[dict] = []
    started = time.perf_counter()
    for page in pages:
        data = page.read_bytes()
        for run_index in range(1, args.runs + 1):
            job = run_page_job(data, "egyptian")
            receipt = json.loads((JOBS_DIR / job.id / "job.json").read_text(encoding="utf-8"))
            final = next((s for s in receipt["stages"] if s["name"] == "final_check"), {})
            runs.append(
                {
                    "page": page.stem,
                    "run": run_index,
                    "job": job.id,
                    "cost": receipt["total_cost_usd"],
                    "ms": receipt["total_ms"],
                    "final_residual": final.get("residual", []),
                    "strategies": {r["id"]: r["strategy"] for r in receipt["regions"]},
                    "regions": [
                        {"id": r["id"], "bbox": r["bbox"], "strategy": r["strategy"]} for r in receipt["regions"]
                    ],
                }
            )
            print(
                f"{page.stem} run{run_index}: {job.id} cost=${receipt['total_cost_usd']:.4f} "
                f"ms={receipt['total_ms']} residual={final.get('residual')}",
                flush=True,
            )

    EVIDENCE.mkdir(parents=True, exist_ok=True)
    (EVIDENCE / "gate-runs.json").write_text(json.dumps(runs, indent=2), encoding="utf-8")
    sheet = build_sheet(runs)
    total_cost = sum(r["cost"] for r in runs)
    total_ms = int((time.perf_counter() - started) * 1000)
    print(f"\nruns={len(runs)} total_cost=${total_cost:.4f} wall={total_ms/1000:.0f}s sheet={sheet}", flush=True)


if __name__ == "__main__":
    main()
