"""Summarise the live Phase 7 runs from their real receipts.

Reads job receipts (no API calls), prints and writes per-page and per-stage medians and
ranges for docs/evidence/phase-7/live-runs.json.

Usage: python backend/scripts/summarise_live_runs.py
"""

from __future__ import annotations

import json
import statistics
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
JOBS = REPO / "backend" / ".cache" / "jobs"
OUT = REPO / "docs" / "evidence" / "phase-7" / "live-runs.json"

RUNS = {
    "comic": {
        "page": "assets/generated/fixtures/01-comic-flat.png",
        "jobs": ["73f1b40b0d02", "f62dcea7dcff", "5024c375e0fe"],
        "wall_measured_ms": [57600, None, None],
    },
    "menu": {
        "page": "assets/generated/fixtures/03-menu-paper.png",
        "jobs": ["ebcee1927e43", "1d1760d039a6", "51282eb309e2"],
        "wall_measured_ms": [None, None, 189000],
    },
}


def main() -> None:
    rows = []
    summary = {}
    for page, spec in RUNS.items():
        page_rows = []
        for index, job_id in enumerate(spec["jobs"]):
            receipt = json.loads((JOBS / job_id / "job.json").read_text(encoding="utf-8"))
            row = {
                "page": page,
                "run": index + 1,
                "job": job_id,
                "demo": bool(receipt.get("demo")),
                "total_ms": receipt["total_ms"],
                "cost_usd": round(receipt["total_cost_usd"], 4),
                "regions": len(receipt.get("regions") or []),
                "wall_measured_ms": spec["wall_measured_ms"][index],
                "warnings": receipt.get("warnings") or [],
                "stages": [
                    {"name": stage["name"], "ms": stage["ms"], "cost_usd": stage.get("cost_usd", 0)}
                    for stage in receipt.get("stages") or []
                ],
            }
            rows.append(row)
            page_rows.append(row)

        stage_names = sorted({stage["name"] for row in page_rows for stage in row["stages"]})
        stages = {}
        for name in stage_names:
            values = [
                stage["ms"]
                for row in page_rows
                for stage in row["stages"]
                if stage["name"] == name
            ]
            stages[name] = {
                "median_ms": int(statistics.median(values)),
                "min_ms": min(values),
                "max_ms": max(values),
                "runs_with_stage": len(values),
                "runs_ms": values,
            }
        totals = [row["total_ms"] for row in page_rows]
        costs = [row["cost_usd"] for row in page_rows]
        walls = [row["wall_measured_ms"] for row in page_rows if row["wall_measured_ms"]]
        summary[page] = {
            "page": spec["page"],
            "runs": len(page_rows),
            "total_median_ms": int(statistics.median(totals)),
            "total_range_ms": [min(totals), max(totals)],
            "cost_median_usd": round(statistics.median(costs), 4),
            "cost_range_usd": [min(costs), max(costs)],
            "regions": page_rows[0]["regions"],
            "wall_measured_runs": len(walls),
            "wall_measured_ms": walls,
            "stages": stages,
        }
        print(page, json.dumps({k: v for k, v in summary[page].items() if k != "stages"}))
        for name, data in stages.items():
            print(f"  {name:18s} median {data['median_ms']:6d} ms  range {data['min_ms']}-{data['max_ms']}")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"runs": rows, "summary": summary, "note": "live runs, DEMO_MODE=0"}, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
