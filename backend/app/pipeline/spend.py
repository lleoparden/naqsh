import datetime
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
LEDGER = REPO / "docs" / "evidence" / "api-spend.jsonl"


def record_spend(label: str, cost_usd: float, **detail) -> None:
    """Append a non-secret cost record for calls made outside a pipeline job."""
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "ts": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "label": label,
        "cost_usd": round(float(cost_usd), 6),
        **detail,
    }
    with LEDGER.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
