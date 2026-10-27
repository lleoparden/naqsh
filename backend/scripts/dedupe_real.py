"""Dedupe on real pages: read-only runs, before/after counts, reasons, cost.

Runs the chalkboard fixture up to 5 times and the public-domain poster up to 3 times
(default), reading regions with Muse Spark only (no segmentation or repaint), so the
counts are cheap and directly comparable to the Phase 5 eval.

Usage: python backend/scripts/dedupe_real.py [chalkboard_runs] [pd_runs]
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PIL import Image  # noqa: E402

from app.pipeline.dedupe import dedupe_report  # noqa: E402
from app.pipeline.regions import read_regions  # noqa: E402
from app.pipeline.spend import record_spend  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
FIXTURES = REPO / "assets" / "generated" / "fixtures"
EVIDENCE = REPO / "docs" / "evidence" / "phase-6"


def main() -> None:
    chalk_runs = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    pd_runs = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    plan = [("04-chalkboard", chalk_runs, "chalkboard"), ("06-real-pd-poster", pd_runs, "pd-poster")]
    results = []
    total = 0.0
    for name, runs, label in plan:
        path = FIXTURES / f"{name}.png"
        with Image.open(path) as image:
            width, height = image.size
        for run in range(1, runs + 1):
            regions, usage = read_regions(path.read_bytes(), width, height, "egyptian")
            cost = usage.spark_cost()
            total += cost
            record_spend(f"dedupe-real {label} run{run}", cost, kind="read", regions=len(regions))
            kept, dropped = dedupe_report(regions)
            row = {
                "fixture": label,
                "run": run,
                "before": len(regions),
                "after": len(kept),
                "dropped": dropped,
                "cost_usd": round(cost, 6),
                "regions": [
                    {"id": r.id, "type": r.type, "text": r.source_text, "bbox": r.bbox.to_list()} for r in regions
                ],
            }
            results.append(row)
            print(
                f"{label} run{run}: {len(regions)} -> {len(kept)} dropped={[d['reason'] for d in dropped]} "
                f"${cost:.4f}",
                flush=True,
            )
    (EVIDENCE / "dedupe-real.json").write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"TOTAL ${total:.4f}")


if __name__ == "__main__":
    main()
