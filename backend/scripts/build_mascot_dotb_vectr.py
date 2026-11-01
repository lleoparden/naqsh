"""Four dot-b-adjacent mascot variants in the Vectr palette (exploration)."""

from __future__ import annotations

import io
import json
import sys
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.pipeline.meta import image_generate
from app.pipeline.spend import record_spend

REPO = Path(__file__).resolve().parents[2]
OUT = Path(r"L:\naqsh-review\mascot\dot-b-vectr")
MANIFEST = REPO / "docs" / "mascot-manifest.json"

BASE = (
    "Original flat-vector mascot: two stacked rounded pebble dots, the smaller sitting on top of the larger "
    "like an Arabic nuqta; the larger pebble has two tiny dot eyes and a small calm smile; no arms, no legs, "
    "no blocky pixel body, no crab shape, no orange or coral body, smooth rounded shapes, thick soft shapes, "
    "centered on a plain background, no text, no letters, no logo, no shadow, readable at 32 px. "
    "Palette strictly: {palette}."
)

VARIANTS = {
    "dotb-vectr-brick": ("brick red #a94a4a body, cream #f3eee8 top dot, dark #1b1b1f outline, cream #f3eee8 background"),
    "dotb-vectr-rose": ("muted rose #e07c7b body, brick red #a94a4a top dot, dark #1b1b1f outline, cream #f3eee8 background"),
    "dotb-vectr-charcoal": ("charcoal #1b1b1f body, muted rose #e07c7b top dot, cream #f3eee8 outline, warm grey #242428 background"),
    "dotb-vectr-cream": ("cream #f3eee8 body, brick red #a94a4a top dot, charcoal #1b1b1f outline, charcoal #202024 background"),
}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    entries = []
    for name, palette in VARIANTS.items():
        prompt = BASE.format(palette=palette)
        raw, usage = image_generate(prompt, size="1024x1536")
        cost = (usage.images or 1) * 0.01
        record_spend(f"mascot variant {name}", cost, kind="image")
        image = Image.open(io.BytesIO(raw)).convert("RGB")
        path = OUT / f"{name}.png"
        image.save(path)
        entries.append(
            {
                "name": name,
                "base": "dot-b",
                "palette": palette,
                "prompt": prompt,
                "file": str(path),
                "cost_usd": round(cost, 4),
            }
        )
        print("generated", name, f"${cost:.2f}")
    data["dotb_variants"] = entries
    MANIFEST.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
