"""Fault-injection test for the Spark visual self-check.

Clean outputs prove nothing about detection, so this script builds known-bad crops:
overflow (drawn at 1.55x), clipping (shifted so ascenders are cut), unreadable
(0.32x), and mistranslated (wrong Arabic for the source). Clean crops are included
to measure false positives. One montage, one vision call, truth table out.

Usage: python backend/scripts/fault_injection.py [job-id]
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.pipeline import shaping  # noqa: E402
from app.pipeline.meta import spark_json  # noqa: E402
from app.pipeline.selfcheck import PROMPT  # noqa: E402
from app.pipeline.types import BBox  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
JOBS = REPO / "backend" / ".cache" / "jobs"
EVIDENCE = REPO / "docs" / "evidence" / "phase-3"
DEFAULT_JOB = "d3dbface16b8"  # comic, egyptian, Phase 3a gate


def _load(job_id: str) -> tuple[dict, Image.Image, Image.Image]:
    folder = JOBS / job_id
    receipt = json.loads((folder / "job.json").read_text(encoding="utf-8"))
    output = Image.open(folder / "output.png").convert("RGB")
    composite = Image.open(folder / "composite.png").convert("RGB")
    return receipt, output, composite


def _crop(base: Image.Image, bbox: list[int], pad: int = 40) -> Image.Image:
    x1, y1, x2, y2 = bbox
    return base.crop((max(0, x1 - pad), max(0, y1 - pad), min(base.width, x2 + pad), min(base.height, y2 + pad)))


def _draw(crop: Image.Image, bbox: list[int], text: str, family: str, size: int, dy: int = 0) -> Image.Image:
    canvas = crop.convert("RGBA")
    line = shaping.shape_line(text, family, size)
    x1, y1, x2, y2 = bbox
    pad = 40
    # bbox is in page coordinates; the crop starts at (x1 - pad, y1 - pad).
    center_x = (x2 - x1) / 2 + pad
    top = (y2 - y1) / 2 + pad + dy
    shaping.draw_line(canvas, line, family, center_x=center_x, top=top, color=(20, 17, 15))
    return canvas.convert("RGB")


def build(job_id: str = DEFAULT_JOB) -> dict:
    receipt, output, composite = _load(job_id)
    regions = receipt["regions"]
    injections: list[dict] = []
    clean: list[dict] = []

    wrong_texts = ["شكراً جزيلاً", "الطقس جميل", "نص آخر تماماً"]

    for index, region in enumerate(regions):
        bbox = region["bbox"]
        family = region["font_family"]
        size = region["font_size"]
        text = region["translation_ar"]
        base = _crop(composite, bbox)

        variants = [
            ("overflow", _draw(base, bbox, text, family, int(size * 1.55)), text),
            ("clipping", _draw(base, bbox, text, family, size, dy=-int(size * 0.55)), text),
            ("unreadable", _draw(base, bbox, text, family, max(8, int(size * 0.2))), text),
            ("bad_translation", _draw(base, bbox, wrong_texts[index % len(wrong_texts)], family, size), wrong_texts[index % len(wrong_texts)]),
        ]
        for kind, image, drawn in variants:
            injections.append(
                {
                    "id": f"f{len(injections) + 1}",
                    "truth": kind,
                    "source": region["source_text"],
                    "arabic": drawn,
                    "image": image,
                }
            )
        clean.append(
            {
                "id": f"c{len(clean) + 1}",
                "truth": "none",
                "source": region["source_text"],
                "arabic": text,
                "image": _crop(output, bbox),
            }
        )

    # One more page's clean crops, so false positives are not measured on one style only.
    chalk, chalk_output, _ = _load("431ee5c7e5f7")
    for region in chalk["regions"]:
        clean.append(
            {
                "id": f"c{len(clean) + 1}",
                "truth": "none",
                "source": region["source_text"],
                "arabic": region["translation_ar"],
                "image": _crop(chalk_output, region["bbox"]),
            }
        )

    return {"injections": injections, "clean": clean}


def montage(items: list[dict]) -> Image.Image:
    label_h = 30
    width = max(item["image"].width for item in items)
    height = sum(item["image"].height + label_h + 6 for item in items)
    sheet = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(sheet)
    y = 0
    for item in items:
        draw.rectangle([0, y, width, y + label_h], fill=(242, 238, 228))
        draw.text((6, y + 8), f"{item['id']} | source: {item['source'][:38]} | arabic: {item['arabic'][:44]}", fill=(20, 17, 15))
        sheet.paste(item["image"], (0, y + label_h))
        y += item["image"].height + label_h + 6
    return sheet


def main() -> None:
    job_id = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_JOB
    data = build(job_id)
    items = data["injections"] + data["clean"]
    sheet = montage(items)
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    sheet_path = EVIDENCE / "fault-injection.png"
    sheet.save(sheet_path)

    buffer_path = EVIDENCE / "fault-injection-montage.png"
    sheet.save(buffer_path)

    payload, usage, raw = spark_json(
        buffer_path.read_bytes(),
        PROMPT.format(count=len(items)),
        max_output_tokens=1600,
    )
    verdicts = {str(v.get("id")): str(v.get("issue") or "unreadable") for v in payload.get("regions") or [] if isinstance(v, dict)}

    rows = []
    for item in items:
        predicted = verdicts.get(item["id"], "missing")
        rows.append({**{k: v for k, v in item.items() if k != "image"}, "predicted": predicted})

    injected = [row for row in rows if row["truth"] != "none"]
    clean = [row for row in rows if row["truth"] == "none"]
    caught = [row for row in injected if row["predicted"] not in ("none", "missing")]
    correct_class = [row for row in injected if row["predicted"] == row["truth"]]
    false_positives = [row for row in clean if row["predicted"] not in ("none", "missing")]

    summary = {
        "job": job_id,
        "injected_regions": len(injected),
        "clean_regions": len(clean),
        "caught": len(caught),
        "catch_rate": round(len(caught) / len(injected), 3) if injected else 0,
        "correct_class": len(correct_class),
        "class_accuracy": round(len(correct_class) / len(injected), 3) if injected else 0,
        "false_positives": len(false_positives),
        "false_positive_rate": round(len(false_positives) / len(clean), 3) if clean else 0,
        "cost_usd": round(usage.spark_cost(), 6),
        "rows": rows,
        "raw": raw,
    }
    (EVIDENCE / "fault-injection.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({k: v for k, v in summary.items() if k not in ("rows", "raw")}, indent=2))
    for row in rows:
        print(f"{row['id']:4s} truth={row['truth']:15s} predicted={row['predicted']}")


if __name__ == "__main__":
    main()
