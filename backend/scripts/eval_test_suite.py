"""Evaluate the English test suite against cached or live pipeline results.

Offline by default: reads docs/evidence/test-suite/<page>.json. With --live it requires
LIVE_MODE=1 and calls the local API once per page (background layers on), then caches the
receipt and document. No tuning: failures and expected-fail pages are reported as-is.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

import requests

REPO = Path(__file__).resolve().parents[2]
SUITE = REPO / "fixtures" / "test-suite"
CACHE = REPO / "docs" / "evidence" / "test-suite"
API = "http://127.0.0.1:8001"


def norm(text: str) -> str:
    text = text.upper()
    text = re.sub(r"[^A-Z0-9 ]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def levenshtein(a: str, b: str) -> int:
    if len(a) < len(b):
        a, b = b, a
    previous = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        current = [i]
        for j, cb in enumerate(b, 1):
            current.append(min(previous[j] + 1, current[j - 1] + 1, previous[j - 1] + (ca != cb)))
        previous = current
    return previous[-1]


def center_inside(region: list[int], box: list[int]) -> bool:
    x = (box[0] + box[2]) / 2
    y = (box[1] + box[3]) / 2
    return region[0] <= x <= region[2] and region[1] <= y <= region[3]


def iou(a: list[int], b: list[int]) -> float:
    x1, y1 = max(a[0], b[0]), max(a[1], b[1])
    x2, y2 = min(a[2], b[2]), min(a[3], b[3])
    if x2 <= x1 or y2 <= y1:
        return 0.0
    inter = (x2 - x1) * (y2 - y1)
    area = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / area


def live_run(page: dict) -> dict:
    image = SUITE / page["image"]
    with image.open("rb") as handle:
        response = requests.post(
            f"{API}/api/localize",
            files={"image": (image.name, handle, "image/jpeg")},
            data={"register": "egyptian", "background_layers": "true"},
            timeout=600,
        )
    response.raise_for_status()
    receipt = response.json()
    document = requests.get(f"{API}/api/jobs/{receipt['id']}/document", timeout=120).json()
    return {"receipt": receipt, "document": document, "captured_at": time.strftime("%Y-%m-%dT%H:%M:%S")}


def evaluate(page: dict, cached: dict) -> dict:
    document = cached["document"]
    receipt = cached["receipt"]
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
            matched.append((region, detected[best], score))
    cers = []
    for region, layer, _score in matched:
        source = layer.get("source_text", "")
        a, b = norm(region["text"]), norm(source)
        cers.append(levenshtein(a, b) / max(1, len(a)))
    bubbles = sum(1 for layer in document["layers"] if layer["kind"] == "bubble")
    return {
        "id": page["id"],
        "expected": page["expected"],
        "features": page.get("features", []),
        "expected_regions": len(expected),
        "detected_regions": len(detected),
        "matched": len(matched),
        "recall": round(len(matched) / max(1, len(expected)), 2) if expected else (1.0 if not detected else 0.0),
        "splits": len(unmatched),
        "cer": round(sum(cers) / len(cers), 3) if cers else None,
        "bubbles": bubbles,
        "seconds": round((receipt.get("total_ms") or 0) / 1000, 1),
        "cost_usd": round(receipt.get("total_cost_usd") or 0, 4),
        "detected_text": [layer.get("source_text", "") for layer in detected],
        "note": page.get("note", ""),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true")
    args = parser.parse_args()
    if args.live and os.getenv("LIVE_MODE", "").strip().lower() not in ("1", "true", "yes"):
        raise SystemExit("live eval requires LIVE_MODE=1")
    CACHE.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((SUITE / "manifest.json").read_text(encoding="utf-8"))
    rows = []
    for page in manifest["pages"]:
        path = CACHE / f"{page['id']}.json"
        if args.live:
            cached = live_run(page)
            path.write_text(json.dumps(cached, indent=2, ensure_ascii=False), encoding="utf-8")
        elif path.is_file():
            cached = json.loads(path.read_text(encoding="utf-8"))
        else:
            print("missing cache", page["id"])
            continue
        rows.append(evaluate(page, cached))
    summary = {
        "pages": len(rows),
        "pass_pages": sum(1 for row in rows if row["expected"] == "pass"),
        "fail_pages": sum(1 for row in rows if row["expected"] == "fail"),
        "mean_recall_pass": round(sum(row["recall"] for row in rows if row["expected"] == "pass") / max(1, sum(1 for row in rows if row["expected"] == "pass")), 2),
        "total_cost_usd": round(sum(row["cost_usd"] for row in rows), 4),
        "results": rows,
    }
    (CACHE / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({k: v for k, v in summary.items() if k != "results"}, indent=2))
    for row in rows:
        print(row["id"], row["expected"], f"regions {row['detected_regions']}/{row['expected_regions']}", f"recall {row['recall']}", f"splits {row['splits']}", f"cer {row['cer']}", f"bubbles {row['bubbles']}", f"{row['seconds']}s", f"${row['cost_usd']}")


if __name__ == "__main__":
    main()
