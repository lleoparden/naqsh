"""Build the Step 0 crop sheet from the step0 runs (no API calls)."""

from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageDraw

REPO = Path(__file__).resolve().parents[2]
JOBS = REPO / "backend" / ".cache" / "jobs"
EVIDENCE = REPO / "docs" / "evidence" / "phase-3"


def crop(image: Image.Image, bbox: list[int], pad: int = 24, max_w: int = 380, max_h: int = 150) -> Image.Image:
    x1, y1, x2, y2 = bbox
    piece = image.crop(
        (max(0, x1 - pad), max(0, y1 - pad), min(image.width, x2 + pad), min(image.height, y2 + pad))
    )
    ratio = min(max_w / piece.width, max_h / piece.height)
    if ratio < 1:
        piece = piece.resize((max(1, int(piece.width * ratio)), max(1, int(piece.height * ratio))), Image.LANCZOS)
    return piece


def main() -> None:
    runs = json.loads((EVIDENCE / "step0-runs.json").read_text(encoding="utf-8"))
    columns = max(len(run["regions"]) for run in runs)
    cell_w, cell_h, label_h, gap = 392, 176, 18, 8
    width = columns * (cell_w + gap) + gap
    height = len(runs) * (cell_h + label_h + gap) + 32
    sheet = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(sheet)
    draw.text((gap, 8), "Step 0: 3 runs per page, 100% crops after cleaning (comic + menu)", fill=(0, 0, 0))
    for row, run in enumerate(runs):
        y = 32 + row * (cell_h + label_h + gap)
        output = Image.open(JOBS / run["job"] / "output.png").convert("RGB")
        draw.text(
            (gap, y),
            f"{run['page']} run{run['run']} | residual: {run['residual'] or 'none'} | ${run['cost']:.4f}",
            fill=(60, 60, 60),
        )
        for column, region in enumerate(run["regions"]):
            x = gap + column * (cell_w + gap)
            piece = crop(output, region["bbox"])
            sheet.paste(piece, (x, y + label_h))
            draw.rectangle([x - 1, y + label_h - 1, x + piece.width, y + label_h + piece.height], outline=(210, 210, 210))
            draw.text((x, y + 3), f"{region['id']} {region['strategy']}", fill=(20, 20, 20))
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    path = EVIDENCE / "step0-crops.png"
    sheet.save(path)
    print("wrote", path)


if __name__ == "__main__":
    main()
