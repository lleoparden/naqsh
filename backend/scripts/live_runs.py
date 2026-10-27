"""Six live runs (comic x3, menu x3) through the API with demo mode off.

Measures wall time, and records per-stage ms and cost from each receipt. Writes
docs/evidence/phase-7/live-runs.json. Usage: python backend/scripts/live_runs.py
"""

from __future__ import annotations

import json
import statistics
import sys
import time
from pathlib import Path

import requests

REPO = Path(__file__).resolve().parents[2]
API = "http://127.0.0.1:8010"
OUT = REPO / "docs" / "evidence" / "phase-7"
PAGES = [
    ("comic", REPO / "assets" / "generated" / "fixtures" / "01-comic-flat.png"),
    ("menu", REPO / "assets" / "generated" / "fixtures" / "03-menu-paper.png"),
]
RUNS = 3


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    for name, path in PAGES:
        raw = path.read_bytes()
        for index in range(1, RUNS + 1):
            started = time.perf_counter()
            response = requests.post(
                f"{API}/api/localize",
                files={"image": (path.name, raw, "image/png")},
                data={"register": "egyptian"},
                timeout=600,
            )
            wall_ms = int((time.perf_counter() - started) * 1000)
            response.raise_for_status()
            job = response.json()
            row = {
                "page": name,
                "run": index,
                "job": job["id"],
                "demo": bool(job.get("demo")),
                "wall_ms": wall_ms,
                "total_ms": job["total_ms"],
                "cost_usd": job["total_cost_usd"],
                "regions": len(job["regions"]),
                "stages": [
                    {"name": stage["name"], "ms": stage["ms"], "cost_usd": stage["cost_usd"]}
                    for stage in job["stages"]
                ],
                "warnings": job.get("warnings") or [],
            }
            rows.append(row)
            print(f"{name} run{index}: {job['id']} wall={wall_ms}ms total={job['total_ms']}ms ${row['cost_usd']:.4f}", flush=True)

    summary = {}
    for name, _path in PAGES:
        page_rows = [row for row in rows if row["page"] == name]
        stage_names = sorted({stage["name"] for row in page_rows for stage in row["stages"]})
        stages = {}
        for stage_name in stage_names:
            values = [
                next(stage["ms"] for stage in row["stages"] if stage["name"] == stage_name)
                for row in page_rows
            ]
            stages[stage_name] = {
                "median_ms": int(statistics.median(values)),
                "min_ms": min(values),
                "max_ms": max(values),
                "runs": values,
            }
        wall = [row["wall_ms"] for row in page_rows]
        cost = [row["cost_usd"] for row in page_rows]
        summary[name] = {
            "runs": len(page_rows),
            "wall_median_ms": int(statistics.median(wall)),
            "wall_range_ms": [min(wall), max(wall)],
            "total_median_ms": int(statistics.median([row["total_ms"] for row in page_rows])),
            "cost_median_usd": round(statistics.median(cost), 4),
            "cost_range_usd": [round(min(cost), 4), round(max(cost), 4)],
            "regions": page_rows[0]["regions"],
            "stages": stages,
        }
    (OUT / "live-runs.json").write_text(
        json.dumps({"runs": rows, "summary": summary}, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
