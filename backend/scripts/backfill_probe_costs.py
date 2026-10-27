"""Backfill the missing cost field on Phase 1 probe receipts.

The probe responses carried usage tokens for Spark and image counts for Muse Image,
but the scripts never wrote a cost field, so `spend_report.py` showed $0.00 for all
probes. This recomputes each receipt's cost from the model, the recorded usage or the
image count, and the published prices (checked 2026-10-27), and marks the value as a
backfill so it is never mistaken for a number the API returned.

Usage: python backend/scripts/backfill_probe_costs.py
"""

from __future__ import annotations

import glob
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PRICE = {
    "spark_input_per_mtok": 1.25,
    "spark_output_per_mtok": 4.25,
    "image_per_image": 0.01,
    "sam_per_image": 2.50 / 1000,
}


def cost_of(data: dict) -> tuple[float, str] | None:
    request = data.get("request") or {}
    model = str(request.get("model") or (data.get("body") or {}).get("model") or "")
    usage = data.get("usage") or (data.get("body") or {}).get("usage") or {}
    if model.startswith("muse-spark"):
        if not usage:
            return None
        prompt = int(usage.get("input_tokens") or 0)
        completion = int(usage.get("output_tokens") or 0)
        cost = prompt / 1_000_000 * PRICE["spark_input_per_mtok"] + completion / 1_000_000 * PRICE["spark_output_per_mtok"]
        return round(cost, 6), f"{prompt} in + {completion} out tokens at published Spark prices"
    if model.startswith("muse-image"):
        images = int(request.get("n") or 1)
        return round(images * PRICE["image_per_image"], 6), f"{images} image(s) at $0.01"
    if model.startswith("sam"):
        return round(PRICE["sam_per_image"], 6), "1 SAM call at $2.50/1000 images"
    return None


def main() -> None:
    changed = 0
    total = 0.0
    for path in sorted(glob.glob(str(REPO / "backend" / ".cache" / "probes" / "*.json"))):
        file = Path(path)
        data = json.loads(file.read_text(encoding="utf-8"))
        if data.get("cost_usd") is not None:
            total += float(data["cost_usd"])
            continue
        result = cost_of(data)
        if result is None:
            print(f"unpriced: {file.name}")
            continue
        cost, basis = result
        data["cost_usd"] = cost
        data["cost_basis"] = basis
        data["cost_backfilled"] = True
        file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        total += cost
        changed += 1
    print(f"backfilled {changed} receipts, total ${total:.4f}")


if __name__ == "__main__":
    main()
