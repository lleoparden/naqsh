"""Generate the two synthetic Phase 5 fixtures (the third is a real PD poster)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.pipeline.meta import image_generate  # noqa: E402
from app.pipeline.spend import record_spend  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "assets" / "generated" / "fixtures"

FIXTURES = [
    {
        "name": "07-comic-sfx",
        "prompt": (
            "An original comic page panel at night on a rooftop: tiny caption boxes in the top "
            "left and top right reading 'THREE DAYS LATER' and 'MEANWHILE...' in small caps, a "
            "large jagged sound effect 'KRAAK!' across the middle in bold stylised lettering, "
            "two silhouetted characters, flat vector colours, thick clean outlines, portrait."
        ),
        "note": "Small captions plus a stylised sound effect.",
    },
    {
        "name": "08-curved-poster",
        "prompt": (
            "An original art deco travel poster with a large headline 'MIDNIGHT EXPRESS' set on a "
            "curve along the top, a tiny footer line 'PRINTED IN CAIRO — 2026' at the bottom, a "
            "geometric sunburst, warm ochre and deep teal, printed paper texture, portrait."
        ),
        "note": "Curved headline plus tiny footer text.",
    },
]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    manifest_path = OUT / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.is_file() else []
    for item in FIXTURES:
        png, usage = image_generate(item["prompt"], size="1024x1536")
        target = OUT / f"{item['name']}.png"
        target.write_bytes(png)
        cost = usage.images * 0.01
        record_spend(f"fixture generation {item['name']}", cost, kind="image")
        manifest.append(
            {
                "name": item["name"],
                "prompt": item["prompt"],
                "note": item["note"],
                "path": str(target.relative_to(REPO)),
                "generated": "muse-image-1.0",
            }
        )
        print(f"{item['name']}: {target.stat().st_size} bytes, ${cost:.4f}")
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print("manifest updated")


if __name__ == "__main__":
    main()
