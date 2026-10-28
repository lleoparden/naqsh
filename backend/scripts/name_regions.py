"""Name each text region with one Spark vision call per page.

Builds a contact sheet of the region crops (labelled t1, t2, ...), asks Muse Spark for a
short descriptive name per region, and caches the names in the job document. Editable in
the editor and shown in the Layers panel.

Usage: python backend/scripts/name_regions.py [job-id ...]
"""

from __future__ import annotations

import io
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PIL import Image, ImageDraw

from app.pipeline.document import load_document, save_document
from app.pipeline.job import JOBS_DIR, load_job
from app.pipeline.meta import spark_json
from app.pipeline.spend import record_spend

REPO = Path(__file__).resolve().parents[2]
EVIDENCE = REPO / "docs" / "evidence" / "ui" / "region-names.json"
DEFAULT_JOBS = ["d3dbface16b8", "e13f9585b24f"]

PROMPT = """This contact sheet shows crops of lettering from one page, each labelled with its id.
For every crop, invent a short English name (2-5 words) describing what it is and, when
visible, who or what it belongs to — for example "Title banner", "Baker's speech bubble",
"Menu price", "Shop sign".

Rules:
- One name per id, no duplicates unless the text is genuinely the same.
- Plain words, no quotes, no punctuation at the end.
- Return strict JSON: {"names": {"t1": "...", "t2": "..."}}
"""


def sheet_for(job_id: str, document) -> bytes:
    folder = JOBS_DIR / job_id
    source = Image.open(folder / "source.png").convert("RGB")
    text_layers = [layer for layer in document.layers if layer.kind == "text"]
    cell_w, cell_h, pad = 260, 120, 8
    cols = 4
    rows = (len(text_layers) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * (cell_w + pad) + pad, rows * (cell_h + pad) + pad + 20), "white")
    draw = ImageDraw.Draw(sheet)
    draw.text((pad, 4), f"job {job_id}", fill="black")
    for index, layer in enumerate(text_layers):
        x1, y1, x2, y2 = layer.box
        crop = source.crop((max(0, x1 - 4), max(0, y1 - 4), min(source.width, x2 + 4), min(source.height, y2 + 4)))
        crop.thumbnail((cell_w, cell_h - 18), Image.LANCZOS)
        col, row = index % cols, index // cols
        x = pad + col * (cell_w + pad)
        y = 20 + pad + row * (cell_h + pad)
        sheet.paste(crop, (x, y + 16))
        draw.text((x, y), f"{layer.id}  {layer.type}", fill="black")
    buffer = io.BytesIO()
    sheet.save(buffer, format="PNG")
    return buffer.getvalue()


def main() -> None:
    job_ids = sys.argv[1:] or DEFAULT_JOBS
    report = []
    total = 0.0
    for job_id in job_ids:
        receipt = load_job(job_id)
        document = load_document(JOBS_DIR / job_id, receipt)
        payload, usage, _raw = spark_json(sheet_for(job_id, document), PROMPT, max_output_tokens=2000)
        cost = usage.spark_cost()
        total += cost
        record_spend(f"region names {job_id}", cost, kind="read", regions=len(document.layers))
        names = payload.get("names") or {}
        applied = {}
        for layer in document.layers:
            if layer.kind != "text":
                continue
            name = str(names.get(layer.id) or "").strip()[:60]
            if name:
                layer.name = name
                applied[layer.id] = name
        save_document(JOBS_DIR / job_id, document)
        report.append({"job": job_id, "cost_usd": round(cost, 6), "names": applied})
        print(job_id, json.dumps(applied, ensure_ascii=False), f"${cost:.4f}")
    EVIDENCE.parent.mkdir(parents=True, exist_ok=True)
    EVIDENCE.write_text(json.dumps({"total_cost_usd": round(total, 6), "pages": report}, indent=2, ensure_ascii=False), encoding="utf-8")
    print("total", f"${total:.4f}")


if __name__ == "__main__":
    main()
