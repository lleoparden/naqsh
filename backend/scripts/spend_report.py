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


def job_total() -> tuple[float, int]:
    total = 0.0
    count = 0
    for path in glob.glob(str(REPO / "backend" / ".cache" / "jobs" / "*" / "job.json")):
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        total += float(data.get("total_cost_usd") or 0)
        count += 1
    return total, count


def probe_total() -> tuple[float, int]:
    total = 0.0
    count = 0
    for path in glob.glob(str(REPO / "backend" / ".cache" / "probes" / "*.json")):
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        total += float(data.get("cost_usd_estimate") or 0)
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
    jobs, job_count = job_total()
    probes, probe_count = probe_total()
    ledger, ledger_count = ledger_total()
    print(f"pipeline jobs   {job_count:3d}  ${jobs:.4f}")
    print(f"probes          {probe_count:3d}  ${probes:.4f}")
    print(f"script ledger   {ledger_count:3d}  ${ledger:.4f}")
    print(f"TOTAL                  ${jobs + probes + ledger:.4f}")


if __name__ == "__main__":
    main()
