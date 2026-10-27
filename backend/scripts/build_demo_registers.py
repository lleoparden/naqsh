"""Fill the MSA register of the demo cache from real re-translation calls.

The cached documents start with MSA equal to the Egyptian text (the pipeline only
translates once). Demo re-translate should replay a real MSA line, so this script
asks Spark for an MSA translation per text layer, writes it into the cached document
and records the spend. It does not touch the receipt (timings/cost of the recorded
run stay as they were).

Usage: python backend/scripts/build_demo_registers.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.pipeline.meta import MetaAPIError, spark_translate  # noqa: E402
from app.pipeline.regions import REGISTERS  # noqa: E402
from app.pipeline.spend import record_spend  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
DEMO = REPO / "fixtures" / "demo"


def main() -> None:
    total = 0.0
    calls = 0
    for folder in sorted(path for path in DEMO.iterdir() if path.is_dir()):
        document_path = folder / "document.json"
        if not document_path.is_file():
            continue
        document = json.loads(document_path.read_text(encoding="utf-8"))
        egyptian = "egyptian"
        for layer in document["layers"]:
            if layer.get("kind") != "text":
                continue
            source = layer.get("source_text") or ""
            egypt = (layer.get("arabic") or {}).get(egyptian) or ""
            if not source or not egypt:
                continue
            if layer["arabic"].get("msa") and layer["arabic"]["msa"] != egypt:
                continue
            try:
                text, usage = spark_translate(
                    source,
                    egypt,
                    "modern standard Arabic for the same line, same length",
                    REGISTERS["msa"],
                )
            except MetaAPIError as exc:
                print(f"{folder.name}/{layer['id']}: failed {exc}")
                continue
            cost = usage.spark_cost()
            total += cost
            calls += 1
            record_spend(f"demo MSA {folder.name}/{layer['id']}", cost, kind="text")
            layer["arabic"]["msa"] = text
            print(f"{folder.name}/{layer['id']}: {text[:40]} ${cost:.4f}")
        document_path.write_text(json.dumps(document, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"{calls} MSA lines, ${total:.4f}")


if __name__ == "__main__":
    main()
