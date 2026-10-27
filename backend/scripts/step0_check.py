"""Step 0: did the gate runs use the coverage-growth fix, and how clean are repeat runs?

Reads the ten gate receipts for the segment-stage marker that only exists after
`coverage.py` landed, then (optionally) runs fresh pages.

Usage:
  python backend/scripts/step0_check.py --verify
  python backend/scripts/step0_check.py --run
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.pipeline.job import JOBS_DIR, run_page_job  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
EVIDENCE = REPO / "docs" / "evidence" / "phase-3"


def verify_gate_runs() -> None:
    runs = json.loads((REPO / "docs" / "evidence" / "phase-4" / "gate-runs.json").read_text(encoding="utf-8"))
    for run in runs:
        receipt = json.loads((JOBS_DIR / run["job"] / "job.json").read_text(encoding="utf-8"))
        segment = next(s for s in receipt["stages"] if s["name"] == "segment")
        print(f"{run['job']} {run['page']:22s} concepts={segment.get('concepts')!r}")


def run_pages(count: int = 3) -> None:
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    pages = [
        REPO / "assets" / "generated" / "fixtures" / "01-comic-flat.png",
        REPO / "assets" / "generated" / "fixtures" / "03-menu-paper.png",
    ]
    summary: list[dict] = []
    for page in pages:
        for index in range(1, count + 1):
            job = run_page_job(page.read_bytes(), "egyptian")
            receipt = json.loads((JOBS_DIR / job.id / "job.json").read_text(encoding="utf-8"))
            final = next((s for s in receipt["stages"] if s["name"] == "final_check"), {})
            entry = {
                "page": page.stem,
                "run": index,
                "job": job.id,
                "cost": receipt["total_cost_usd"],
                "ms": receipt["total_ms"],
                "residual": final.get("residual", []),
                "notes": final.get("notes", {}),
                "strategies": {r["id"]: r["strategy"] for r in receipt["regions"]},
                "regions": [
                    {"id": r["id"], "bbox": r["bbox"], "strategy": r["strategy"]} for r in receipt["regions"]
                ],
            }
            summary.append(entry)
            print(f"{page.stem} run{index}: {job.id} ${entry['cost']:.4f} residual={entry['residual']}", flush=True)
    (EVIDENCE / "step0-runs.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--run", action="store_true")
    args = parser.parse_args()
    if args.verify:
        verify_gate_runs()
    if args.run:
        run_pages(3)


if __name__ == "__main__":
    main()
