"""Running API spend, from receipts plus a ledger for script calls.

- Pipeline jobs: `backend/.cache/jobs/*/job.json` → `total_cost_usd`
- Probes: `backend/.cache/probes/*.json` → `cost_usd_estimate`
- Script calls (fault injection, ad-hoc checks): `docs/evidence/api-spend.jsonl`

Usage: python backend/scripts/spend_report.py
"""

from __future__ import annotations

import glob
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
LEDGER = REPO / "docs" / "evidence" / "api-spend.jsonl"


def job_totals() -> tuple[float, int, float, int]:
    """(real spend, real count, demo replay cost, demo count).

    Demo jobs copy the recorded receipt, so their total_cost_usd was already paid by
    the original run and must never be added again.
    """
    total = 0.0
    count = 0
    demo_total = 0.0
    demo_count = 0
    for path in glob.glob(str(REPO / "backend" / ".cache" / "jobs" / "*" / "job.json")):
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        cost = float(data.get("total_cost_usd") or 0)
        if data.get("demo"):
            demo_total += cost
            demo_count += 1
            continue
        total += cost
        count += 1
    return total, count, demo_total, demo_count


def probe_total() -> tuple[float, int]:
    total = 0.0
    count = 0
    for path in glob.glob(str(REPO / "backend" / ".cache" / "probes" / "*.json")):
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        value = data.get("cost_usd")
        if value is None:
            # Legacy receipts: cost recomputed from model + usage/image count.
            value = data.get("cost_usd_estimate")
        total += float(value or 0)
        count += 1
    return total, count


def ledger_total() -> tuple[float, int]:
    if not LEDGER.is_file():
        return 0.0, 0
    total = 0.0
    count = 0
    for line in LEDGER.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        entry = json.loads(line)
        total += float(entry.get("cost_usd") or 0)
        count += 1
    return total, count


def main() -> None:
    jobs, job_count, demo_cost, demo_count = job_totals()
    probes, probe_count = probe_total()
    ledger, ledger_count = ledger_total()
    print(f"pipeline jobs   {job_count:3d}  ${jobs:.4f}")
    print(f"demo replays    {demo_count:3d}  ${demo_cost:.4f}  (recorded cost, not new spend)")
    print(f"probes          {probe_count:3d}  ${probes:.4f}")
    print(f"script ledger   {ledger_count:3d}  ${ledger:.4f}")
    print(f"TOTAL                  ${jobs + probes + ledger:.4f}")


if __name__ == "__main__":
    main()
