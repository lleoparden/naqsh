"""Post-change variance: three live comic runs and three live menu runs.

Writes docs/evidence/phase-8/variance.json incrementally so a long run can be watched.
Usage: python backend/scripts/variance_runs.py
"""

from __future__ import annotations

import json
import statistics
import time
from pathlib import Path

import requests

REPO = Path(__file__).resolve().parents[2]
API = "http://127.0.0.1:8010"
OUT = REPO / "docs" / "evidence" / "phase-8" / "variance.json"
PAGES = [
    ("comic", REPO / "assets" / "generated" / "fixtures" / "01-comic-flat.png"),
    ("menu", REPO / "assets" / "generated" / "fixtures" / "03-menu-paper.png"),
]


def save(rows: list[dict]) -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"runs": rows}, indent=2), encoding="utf-8")


def main() -> None:
    rows: list[dict] = []
    for name, path in PAGES:
        raw = path.read_bytes()
        for index in range(1, 4):
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
                "stage_ms_sum": job.get("stage_ms_sum"),
                "cost_usd": round(job["total_cost_usd"], 4),
                "regions": len(job["regions"]),
                "stages": [{"name": s["name"], "ms": s["ms"]} for s in job["stages"]],
                "warnings": job.get("warnings") or [],
            }
            rows.append(row)
            save(rows)
            print(json.dumps({k: row[k] for k in ("page", "run", "job", "wall_ms", "total_ms", "cost_usd", "regions")}), flush=True)
    print("done")


if __name__ == "__main__":
    main()
