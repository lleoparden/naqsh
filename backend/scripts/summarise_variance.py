"""Combine every post-change live run into one variance table.

Comic: the three new runs only (there were no post-change comic runs before).
Menu: the two runs in menu-after.json plus the three new ones.

Usage: python backend/scripts/summarise_variance.py
"""

from __future__ import annotations

import json
import statistics
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
EVIDENCE = REPO / "docs" / "evidence" / "phase-8"


def load(name: str) -> list[dict]:
    data = json.loads((EVIDENCE / name).read_text(encoding="utf-8"))
    return data["runs"] if isinstance(data, dict) and "runs" in data else data


def main() -> None:
    variance = load("variance.json")
    menu_after = json.loads((EVIDENCE / "menu-after.json").read_text(encoding="utf-8"))["runs"]
    menu_after = [{**row, "page": "menu", "source": "menu-after.json"} for row in menu_after]
    comic = [{**row, "source": "variance.json"} for row in variance if row["page"] == "comic"]
    menu = [{**row, "source": "variance.json"} for row in variance if row["page"] == "menu"] + menu_after

    summary = {}
    for page, rows in (("comic", comic), ("menu", menu)):
        walls = [row["wall_ms"] for row in rows]
        totals = [row["total_ms"] for row in rows]
        costs = [row["cost_usd"] for row in rows]
        stage_names = sorted({stage["name"] for row in rows for stage in row["stages"]})
        stages = {}
        for name in stage_names:
            values = [stage["ms"] for row in rows for stage in row["stages"] if stage["name"] == name]
            stages[name] = {
                "median_ms": int(statistics.median(values)),
                "min_ms": min(values),
                "max_ms": max(values),
                "runs": len(values),
            }
        summary[page] = {
            "runs": len(rows),
            "walls_ms": walls,
            "median_wall_ms": int(statistics.median(walls)),
            "wall_range_ms": [min(walls), max(walls)],
            "median_total_ms": int(statistics.median(totals)),
            "total_range_ms": [min(totals), max(totals)],
            "median_cost_usd": round(statistics.median(costs), 4),
            "cost_range_usd": [min(costs), max(costs)],
            "regions": sorted({row["regions"] for row in rows}),
            "stages": stages,
        }

    out = {"comic": summary["comic"], "menu": summary["menu"], "runs": comic + menu}
    (EVIDENCE / "variance-summary.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    for page in ("comic", "menu"):
        s = summary[page]
        print(
            f"{page}: {s['runs']} runs, wall median {s['median_wall_ms']/1000:.1f}s "
            f"range {s['wall_range_ms'][0]/1000:.1f}-{s['wall_range_ms'][1]/1000:.1f}s, "
            f"cost median ${s['median_cost_usd']:.4f}, regions {s['regions']}"
        )
        for name, stage in s["stages"].items():
            print(f"  {name:18s} {stage['median_ms']:6d} ms  ({stage['min_ms']}-{stage['max_ms']}, n={stage['runs']})")


if __name__ == "__main__":
    main()
