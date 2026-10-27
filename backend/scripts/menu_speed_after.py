"""Two live menu runs after the speed work, with per-stage receipts.

Usage: python backend/scripts/menu_speed_after.py
"""

from __future__ import annotations

import json
import statistics
import time
from pathlib import Path

import requests

REPO = Path(__file__).resolve().parents[2]
API = "http://127.0.0.1:8010"
PAGE = REPO / "assets" / "generated" / "fixtures" / "03-menu-paper.png"
OUT = REPO / "docs" / "evidence" / "phase-8" / "menu-after.json"


def main() -> None:
    raw = PAGE.read_bytes()
    rows = []
    for index in range(1, 3):
        started = time.perf_counter()
        response = requests.post(
            f"{API}/api/localize",
            files={"image": (PAGE.name, raw, "image/png")},
            data={"register": "egyptian"},
            timeout=600,
        )
        wall_ms = int((time.perf_counter() - started) * 1000)
        response.raise_for_status()
        job = response.json()
        row = {
            "run": index,
            "job": job["id"],
            "wall_ms": wall_ms,
            "total_ms": job["total_ms"],
            "cost_usd": round(job["total_cost_usd"], 4),
            "regions": len(job["regions"]),
            "stages": [{"name": s["name"], "ms": s["ms"], "cost_usd": s.get("cost_usd", 0)} for s in job["stages"]],
            "warnings": job.get("warnings") or [],
        }
        rows.append(row)
        print(json.dumps({k: row[k] for k in ("run", "job", "wall_ms", "total_ms", "cost_usd", "regions")}), flush=True)
    totals = [row["total_ms"] for row in rows]
    walls = [row["wall_ms"] for row in rows]
    summary = {
        "runs": rows,
        "median_total_ms": int(statistics.median(totals)),
        "median_wall_ms": int(statistics.median(walls)),
        "range_total_ms": [min(totals), max(totals)],
        "regions": [row["regions"] for row in rows],
        "cost_usd": [row["cost_usd"] for row in rows],
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print("median total", summary["median_total_ms"], "wall", summary["median_wall_ms"])


if __name__ == "__main__":
    main()
