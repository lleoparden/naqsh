"""Text-only parity: diffs inside the union of text boxes.

Renders the document twice - server (PIL + HarfBuzz) and browser (headless Chrome,
Blink, which shapes Arabic with HarfBuzz) - and reports the difference only inside
the union of the text boxes, plus per-region numbers. Also usable on the gate jobs to
compare the exported SVG render with the editor/server render.

Usage: python backend/scripts/text_parity.py <job-id> [...]
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.pipeline import document as document_module  # noqa: E402
from app.pipeline import export as export_module  # noqa: E402
from app.pipeline.job import JOBS_DIR, load_job  # noqa: E402
from app.pipeline.types import BBox  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from parity_check import render_browser  # noqa: E402

EVIDENCE = Path(__file__).resolve().parents[2] / "docs" / "evidence" / "phase-6"


def text_mask(doc, pad: int = 2) -> np.ndarray:
    mask = Image.new("L", (doc.width, doc.height), 0)
    draw = ImageDraw.Draw(mask)
    for layer in doc.layers:
        if layer.kind != "text" or layer.action == "skip" or not layer.visible:
            continue
        x1, y1, x2, y2 = layer.box
        draw.rectangle([x1 - pad, y1 - pad, x2 + pad, y2 + pad], fill=255)
    return np.asarray(mask) > 0


def main() -> None:
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    rows = []
    for job_id in sys.argv[1:]:
        receipt = load_job(job_id)
        folder = JOBS_DIR / job_id
        doc = document_module.load_document(folder, receipt)
        server = export_module.render_png(doc, folder)
        svg = export_module.build_svg(doc, folder)
        browser_png = EVIDENCE / f"textparity-{job_id}-browser.png"
        render_browser(svg, doc.width, doc.height, browser_png)
        browser = Image.open(browser_png).convert("RGB").resize(server.size)

        mask = text_mask(doc)
        diff = np.abs(np.asarray(server, dtype=np.int16) - np.asarray(browser, dtype=np.int16)).max(axis=2)
        inside = diff[mask]
        per_region = []
        for layer in doc.layers:
            if layer.kind != "text" or not layer.lines:
                continue
            x1, y1, x2, y2 = layer.box
            sub = diff[max(0, y1 - 2) : y2 + 2, max(0, x1 - 2) : x2 + 2]
            per_region.append(
                {
                    "id": layer.id,
                    "action": layer.action,
                    "mean": round(float(sub.mean()), 2),
                    "over_40": round(float((sub > 40).mean() * 100), 3),
                }
            )
        row = {
            "job": job_id,
            "renderer": "headless Chrome (Blink + HarfBuzz), @font-face bundled fonts",
            "text_pixels": int(mask.sum()),
            "mean_abs_diff": round(float(inside.mean()), 2),
            "pixels_over_40": round(float((inside > 40).mean() * 100), 3),
            "per_region": per_region,
        }
        rows.append(row)
        visual = Image.fromarray(np.clip(diff * 2, 0, 255).astype("uint8"))
        visual.save(EVIDENCE / f"textparity-{job_id}-diff.png")
        # Crop the text band for an at-a-glance view.
        ys, xs = np.where(mask)
        if len(xs):
            box = (int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max()))
            visual.crop(box).save(EVIDENCE / f"textparity-{job_id}-diff-crop.png")
        print(json.dumps({k: v for k, v in row.items() if k != "per_region"}))
    (EVIDENCE / "text-parity.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
