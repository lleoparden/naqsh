"""Run the three public-domain poster sources live once and record metrics."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import requests
from PIL import Image

REPO = Path(__file__).resolve().parents[2]
SOURCES = Path(r"L:\naqsh-review\demo-v3\sources")
OUT = Path(r"L:\naqsh-review\demo-v3\results")
CACHE = REPO / "docs" / "evidence" / "demo-v3"
API = "http://127.0.0.1:8001"


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


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    CACHE.mkdir(parents=True, exist_ok=True)
    rows = []
    for path in sorted(SOURCES.iterdir()):
        if path.suffix.lower() not in (".jpg", ".jpeg", ".png", ".tif", ".tiff"):
            continue
        with path.open("rb") as handle:
            response = requests.post(
                f"{API}/api/localize",
                files={"image": (path.name, handle, "image/jpeg")},
                data={"register": "egyptian", "background_layers": "true"},
                timeout=600,
            )
        if response.status_code != 200:
            rows.append({"file": path.name, "error": f"HTTP {response.status_code}: {response.text[:200]}"})
            print("FAIL", path.name, response.text[:160])
            continue
        receipt = response.json()
        document = requests.get(f"{API}/api/jobs/{receipt['id']}/document", timeout=120).json()
        folder = REPO / "backend" / ".cache" / "jobs" / receipt["id"]
        result = folder / "output.png"
        if result.is_file():
            Image.open(result).convert("RGB").save(OUT / f"{path.stem}.png")
        (CACHE / f"{path.stem}.json").write_text(
            json.dumps({"receipt": receipt, "document": document}, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        verify = next((stage for stage in receipt.get("stages", []) if stage.get("name") == "verify"), {})
        rows.append(
            {
                "file": path.name,
                "id": receipt["id"],
                "regions": len(document.get("layers", [])),
                "text_layers": sum(1 for layer in document["layers"] if layer["kind"] == "text"),
                "bubbles": sum(1 for layer in document["layers"] if layer["kind"] == "bubble"),
                "seconds": round((receipt.get("total_ms") or 0) / 1000, 1),
                "cost_usd": round(receipt.get("total_cost_usd") or 0, 4),
                "plate_diff_outside": plate_diff(folder),
                "verify": verify.get("notes") or verify.get("residual") or "no detail",
                "result": str(OUT / f"{path.stem}.png"),
            }
        )
        print(path.name, rows[-1]["text_layers"], rows[-1]["seconds"], rows[-1]["cost_usd"])
    (CACHE / "summary.json").write_text(json.dumps({"posters": rows}, indent=2, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
