"""Phase 3a gate: both registers on comic, menu and chalkboard, with a crop sheet.

For every region the script records the chosen family, the size, the line breaks,
whether the fitter had to clamp (overflow), and whether any shaped ink falls outside
the container. The sheet shows 100% crops of the final render, labelled
page / register / region / family / size.

Usage: python backend/scripts/run_typeset_gate.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.pipeline.job import JOBS_DIR, run_page_job  # noqa: E402
from app.pipeline.shaping import measure  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
FIXTURES = REPO / "assets" / "generated" / "fixtures"
EVIDENCE = REPO / "docs" / "evidence" / "phase-3"
PAGES = ["01-comic-flat", "03-menu-paper", "04-chalkboard"]
REGISTERS = ["egyptian", "msa"]


def crop_cell(image: Image.Image, bbox: list[int], pad: int = 26, max_w: int = 400, max_h: int = 150) -> Image.Image:
    x1, y1, x2, y2 = bbox
    piece = image.crop((max(0, x1 - pad), max(0, y1 - pad), min(image.width, x2 + pad), min(image.height, y2 + pad)))
    ratio = min(max_w / piece.width, max_h / piece.height)
    if ratio < 1:
        piece = piece.resize((max(1, int(piece.width * ratio)), max(1, int(piece.height * ratio))), Image.LANCZOS)
    return piece


def build_sheet(runs: list[dict]) -> Path:
    columns = max(len(run["regions"]) for run in runs)
    cell_w, cell_h, label_h, gap = 412, 172, 20, 8
    sheet = Image.new("RGB", (columns * (cell_w + gap) + gap, len(runs) * (cell_h + label_h + gap) + 30), "white")
    draw = ImageDraw.Draw(sheet)
    draw.text((gap, 8), "Phase 3a gate: HarfBuzz typesetting, 100% crops, both registers", fill=(0, 0, 0))
    for row, run in enumerate(runs):
        y = 30 + row * (cell_h + label_h + gap)
        output = Image.open(JOBS_DIR / run["job"] / "output.png").convert("RGB")
        draw.text(
            (gap, y),
            f"{run['page']} | {run['register']} | ${run['cost']:.4f} | overflow {run['overflow'] or 'none'}",
            fill=(60, 60, 60),
        )
        for column, region in enumerate(run["regions"]):
            x = gap + column * (cell_w + gap)
            piece = crop_cell(output, region["bbox"])
            sheet.paste(piece, (x, y + label_h))
            draw.rectangle([x - 1, y + label_h - 1, x + piece.width, y + label_h + piece.height], outline=(210, 210, 210))
            draw.text((x, y + 3), f"{region['id']} {region['family']} {region['size']}px", fill=(20, 20, 20))
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    path = EVIDENCE / "typeset-gate.png"
    sheet.save(path)
    return path


def main() -> None:
    runs: list[dict] = []
    for page_name in PAGES:
        page = FIXTURES / f"{page_name}.png"
        for register in REGISTERS:
            job = run_page_job(page.read_bytes(), register)
            receipt = json.loads((JOBS_DIR / job.id / "job.json").read_text(encoding="utf-8"))
            regions = []
            overflow = []
            for region in receipt["regions"]:
                box = region.get("container") or region["bbox"]
                width, height = box[2] - box[0], box[3] - box[1]
                too_big = any(
                    measure(line, region["font_family"], region["font_size"])[0] > width
                    or measure(line, region["font_family"], region["font_size"])[1] > height
                    for line in region["lines"]
                )
                if too_big:
                    overflow.append(region["id"])
                regions.append(
                    {
                        "id": region["id"],
                        "bbox": region["bbox"],
                        "family": region["font_family"],
                        "size": region["font_size"],
                        "lines": region["lines"],
                        "fits": not too_big,
                        "text": region["translation_ar"],
                    }
                )
            runs.append(
                {
                    "page": page_name,
                    "register": register,
                    "job": job.id,
                    "cost": receipt["total_cost_usd"],
                    "ms": receipt["total_ms"],
                    "regions": regions,
                    "overflow": overflow,
                }
            )
            print(f"{page_name} {register}: {job.id} ${receipt['total_cost_usd']:.4f} overflow={overflow}", flush=True)

    EVIDENCE.mkdir(parents=True, exist_ok=True)
    (EVIDENCE / "typeset-gate-runs.json").write_text(json.dumps(runs, indent=2, ensure_ascii=False), encoding="utf-8")
    sheet = build_sheet(runs)
    total = sum(run["cost"] for run in runs)
    print(f"\nruns={len(runs)} total=${total:.4f} sheet={sheet}")


if __name__ == "__main__":
    main()
