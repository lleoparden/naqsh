"""Run the four selected v4 pages plus the Phase 1 baker panel live once."""

from __future__ import annotations

import json
import re
from pathlib import Path

import numpy as np
import requests
from PIL import Image

REPO = Path(__file__).resolve().parents[2]
PAGES = REPO / "fixtures" / "demo-v4"
CACHE = REPO / "docs" / "evidence" / "demo-v4"
OUT = Path(r"L:\naqsh-review\demo-v4\results")
API = "http://127.0.0.1:8001"

BAKER = {
    "id": "phase1-baker",
    "image": REPO / "assets" / "generated" / "test-panel.png",
    "regions": [
        {"id": "t1", "box": [306, 330, 982, 457], "text": "CHAPTER ONE"},
        {"id": "t2", "box": [131, 520, 465, 732], "text": "FRESH BREAD?"},
        {"id": "t3", "box": [778, 528, 1178, 712], "text": "EVERY MORNING"},
    ],
}


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
    return round(float(np.abs(source - plate)[~union].mean()), 3)


def run(page: dict) -> dict:
    path = Path(page["image"]) if "image" in page and str(page["image"]).startswith("L:") else PAGES / page["image"]
    with path.open("rb") as handle:
        response = requests.post(
            f"{API}/api/localize",
            files={"image": (path.name, handle, "image/png" if path.suffix == ".png" else "image/jpeg")},
            data={"register": "egyptian", "background_layers": "true"},
            timeout=600,
        )
    response.raise_for_status()
    receipt = response.json()
    document = requests.get(f"{API}/api/jobs/{receipt['id']}/document", timeout=120).json()
    folder = REPO / "backend" / ".cache" / "jobs" / receipt["id"]
    result = folder / "output.png"
    if result.is_file():
        Image.open(result).convert("RGB").save(OUT / f"{page['id']}.png")
    detected = [layer for layer in document["layers"] if layer["kind"] == "text" and layer.get("action") != "skip"]
    unmatched = set(range(len(detected)))
    cers = []
    matched = 0
    for region in page["regions"]:
        best, score = None, 0.0
        for index in unmatched:
            value = 1.0 if center_inside(region["box"], detected[index]["box"]) else iou(region["box"], detected[index]["box"])
            if value > score:
                best, score = index, value
        if best is not None and score > 0.15:
            unmatched.discard(best)
            matched += 1
            a, b = norm(region["text"]), norm(detected[best].get("source_text", ""))
            cers.append(levenshtein(a, b) / max(1, len(a)))
    verify = next((stage for stage in receipt.get("stages", []) if stage.get("name") == "verify"), {})
    return {
        "id": page["id"],
        "expected": len(page["regions"]),
        "detected": len(detected),
        "recall": round(matched / max(1, len(page["regions"])), 2),
        "cer": round(sum(cers) / len(cers), 3) if cers else None,
        "splits": len(unmatched),
        "bubbles": sum(1 for layer in document["layers"] if layer["kind"] == "bubble"),
        "seconds": round((receipt.get("total_ms") or 0) / 1000, 1),
        "cost_usd": round(receipt.get("total_cost_usd") or 0, 4),
        "plate_diff_outside": plate_diff(folder),
        "verify": verify.get("notes") or verify.get("residual") or "no detail",
        "result": str(OUT / f"{page['id']}.png"),
    }


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    CACHE.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((PAGES / "manifest.json").read_text(encoding="utf-8"))
    rows = []
    for page in [p for p in manifest["pages"] if p.get("selected")]:
        rows.append(run(page))
        print(rows[-1])
    rows.append(run(BAKER))
    print(rows[-1])
    (CACHE / "summary.json").write_text(json.dumps({"pages": rows}, indent=2, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
