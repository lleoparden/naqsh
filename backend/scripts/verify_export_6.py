"""Round-trip verification for the exported gate artifacts (offline)."""

from __future__ import annotations

import json
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

REPO = Path(__file__).resolve().parents[2]
EVIDENCE = REPO / "docs" / "evidence" / "phase-6"
NS = {"svg": "http://www.w3.org/2000/svg"}


def main() -> None:
    gate = json.loads((EVIDENCE / "gate.json").read_text(encoding="utf-8"))
    rows = []
    for run in gate:
        job = run["job"]
        svg_path = EVIDENCE / f"gate-{job}.svg"
        root = ET.fromstring(svg_path.read_text(encoding="utf-8"))
        texts = [element.text or "" for element in root.findall(".//svg:text", NS)]
        layer_ids = [element.get("id") for element in root.findall(".//svg:g", NS) if (element.get("id") or "").startswith("layer-")]
        covers = root.findall(".//svg:rect", NS)
        with zipfile.ZipFile(EVIDENCE / f"gate-{job}.zip") as archive:
            names = archive.namelist()
            fonts = [name for name in names if name.startswith("fonts/") and name.endswith(".ttf")]
            licenses = [name for name in names if "OFL" in name]
            outlined = archive.read("export-outlined.svg").decode("utf-8")
        outlined_texts = ET.fromstring(outlined).findall(".//svg:text", NS)
        rows.append(
            {
                "job": job,
                "xml_parsed": True,
                "text_elements": len(texts),
                "text_layer_groups": len(layer_ids),
                "cover_rects": len(covers),
                "zip_files": sorted(names),
                "fonts_in_zip": len(fonts),
                "licenses_in_zip": len(licenses),
                "outlined_has_text": len(outlined_texts) > 0,
                "outlined_has_paths": len(ET.fromstring(outlined).findall(".//svg:path", NS)) > 0,
                "texts": texts,
            }
        )
        print(
            f"{job}: text={len(texts)} layers={len(layer_ids)} covers={len(covers)} "
            f"fonts={len(fonts)} licenses={len(licenses)} outlined_text={len(outlined_texts)}"
        )
    (EVIDENCE / "verify.json").write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
