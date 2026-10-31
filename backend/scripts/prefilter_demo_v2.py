"""Run the six v2 demo candidates live once, prefilter them and build a large contact sheet."""

from __future__ import annotations

import io
import json
import re
import time
from pathlib import Path

import numpy as np
import requests
from PIL import Image, ImageDraw, ImageFont

REPO = Path(__file__).resolve().parents[2]
PAGES = REPO / "fixtures" / "demo-v2"
CACHE = REPO / "docs" / "evidence" / "demo-v2"
OUT = Path(r"L:\naqsh-review\demo-candidates-v2")
API = "http://127.0.0.1:8001"
FONT = REPO / "assets" / "fonts" / "Inter-Variable.ttf"


def norm(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^A-Za-z0-9 ]+", " ", text.upper())).strip()


def levenshtein(a: str, b: str) -> int:
    if len(a) < len(b):
        a, b = b, a
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def iou(a, b) -> float:
    x1, y1 = max(a[0], b[0]), max(a[1], b[1])
    x2, y2 = min(a[2], b[2]), min(a[3], b[3])
    if x2 <= x1 or y2 <= y1:
        return 0.0
    inter = (x2 - x1) * (y2 - y1)
    return inter / ((a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter)


def center_inside(region, box) -> bool:
    x, y = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
    return region[0] <= x <= region[2] and region[1] <= y <= region[3]


def plate_diff(folder: Path) -> float | None:
    source = np.asarray(Image.open(folder / "source.png").convert("RGB"), dtype=np.int16)
    plate = np.asarray(Image.open(folder / "plate.png").convert("RGB"), dtype=np.int16)
    masks = [np.asarray(Image.open(p).convert("L")) > 127 for p in folder.glob("mask-*.png")]
    if not masks:
        return None
    union = np.zeros(masks[0].shape, dtype=bool)
    for mask in masks:
        union |= mask
    outside = ~union
    return round(float(np.abs(source - plate)[outside].mean()), 3)


def main() -> None:
    CACHE.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((PAGES / "manifest.json").read_text(encoding="utf-8"))
    rows = []
    for page in manifest["pages"]:
        image_path = PAGES / page["image"]
        with image_path.open("rb") as handle:
            response = requests.post(
                f"{API}/api/localize",
                files={"image": (image_path.name, handle, "image/jpeg")},
                data={"register": "egyptian", "background_layers": "true"},
                timeout=600,
            )
        if response.status_code != 200:
            print(page["id"], "FAILED", response.status_code, response.text[:160])
            rows.append(
                {
                    "id": page["id"],
                    "regions_expected": len(page["regions"]),
                    "regions_detected": 0,
                    "recall": 0.0,
                    "cer": None,
                    "splits": 0,
                    "seconds": None,
                    "cost_usd": 0.0,
                    "verify": f"HTTP {response.status_code}: {response.text[:160]}",
                    "plate_diff_outside": None,
                    "pass": False,
                    "result": "",
                }
            )
            continue
        receipt = response.json()
        document = requests.get(f"{API}/api/jobs/{receipt['id']}/document", timeout=120).json()
        folder = REPO / "backend" / ".cache" / "jobs" / receipt["id"]
        (CACHE / f"{page['id']}.json").write_text(
            json.dumps({"receipt": receipt, "document": document}, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        detected = [layer for layer in document["layers"] if layer["kind"] == "text" and layer.get("action") != "skip"]
        expected = page["regions"]
        unmatched = set(range(len(detected)))
        matched = []
        for region in expected:
            best, score = None, 0.0
            for index in unmatched:
                value = 1.0 if center_inside(region["box"], detected[index]["box"]) else iou(region["box"], detected[index]["box"])
                if value > score:
                    best, score = index, value
            if best is not None and score > 0.15:
                unmatched.discard(best)
                matched.append((region, detected[best]))
        cers = []
        for region, layer in matched:
            a, b = norm(region["text"]), norm(layer.get("source_text", ""))
            cers.append(levenshtein(a, b) / max(1, len(a)))
        recall = round(len(matched) / max(1, len(expected)), 2)
        cer = round(sum(cers) / len(cers), 3) if cers else None
        seconds = round((receipt.get("total_ms") or 0) / 1000, 1)
        verify = next((stage for stage in receipt.get("stages", []) if stage.get("name") == "verify"), {})
        result_path = folder / "output.png"
        passed = recall == 1.0 and cer == 0.0 and seconds < 60
        rows.append(
            {
                "id": page["id"],
                "regions_expected": len(expected),
                "regions_detected": len(detected),
                "recall": recall,
                "cer": cer,
                "splits": len(unmatched),
                "seconds": seconds,
                "cost_usd": round(receipt.get("total_cost_usd") or 0, 4),
                "verify": verify.get("notes") or verify.get("residual") or "no verify detail",
                "plate_diff_outside": plate_diff(folder),
                "pass": passed,
                "result": str(result_path),
            }
        )
        print(page["id"], rows[-1])

    # Large contact sheet: one page per row, source | result, readable labels.
    thumb_w = 620
    items = []
    for row in rows:
        src = Image.open(PAGES / next(p["image"] for p in manifest["pages"] if p["id"] == row["id"])).convert("RGB")
        res = Image.open(row["result"]).convert("RGB") if row["result"] else src.copy()
        h = int(src.height * thumb_w / src.width)
        items.append((src.resize((thumb_w, h)), res.resize((thumb_w, h)), row))
    row_h = items[0][0].height
    sheet = Image.new("RGB", (thumb_w * 2 + 80, (row_h + 110) * len(items) + 30), "white")
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.truetype(str(FONT), 24)
    for index, (src, res, row) in enumerate(items):
        y = 20 + index * (row_h + 110)
        sheet.paste(src, (20, y))
        sheet.paste(res, (thumb_w + 60, y))
        label = (
            f"{row['id']}  {'PASS' if row['pass'] else 'FAIL'}  recall {row['recall']}  CER {row['cer']}  "
            f"{row['seconds']}s  ${row['cost_usd']:.4f}"
        )
        draw.text((20, y + row_h + 10), label, font=font, fill=(0, 0, 0))
        draw.text((20, y + row_h + 50), f"verify: {str(row['verify'])[:90]}", font=ImageFont.truetype(str(FONT), 18), fill=(80, 80, 80))
    sheet.save(OUT / "contact-sheet.jpg", "JPEG", quality=90)
    (CACHE / "summary.json").write_text(json.dumps({"pages": rows}, indent=2, ensure_ascii=False), encoding="utf-8")
    print("sheet", OUT / "contact-sheet.jpg")


if __name__ == "__main__":
    main()
