"""Generate 8 original mascot concepts for Naqsh (name = imprint/engraving)."""

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
OUT = Path(r"L:\naqsh-review\mascot\concepts")
MANIFEST = REPO / "docs" / "mascot-manifest.json"

STYLE = (
    "Original flat-vector mascot concept, single cute character, smooth rounded shapes, tiny dot eyes, "
    "no mouth or a tiny simple mouth, no arms or legs, no blocky pixel body, no crab shape, "
    "no orange or coral body, palette #5B6CFF indigo plus cool grey/cream neutral, thick soft shapes, "
    "centered on a plain very light cool-grey background, no text, no letters, no logo, no shadow, "
    "readable as a tiny icon, portrait."
)

CONCEPTS = {
    "dot-a": ("A single rounded blob shaped like a soft teardrop dot with one tiny flat side, like an Arabic nuqta; "
              "two tiny dot eyes and a small calm smile. " + STYLE),
    "dot-b": ("A pair of stacked rounded pebble-dots, the smaller resting on the larger like a punctuation mark; "
              "the larger has two tiny dot eyes and a small smile. " + STYLE),
    "ink-a": ("A friendly ink drop with a rounded bulb and a soft pointed top, a glossy highlight, tiny dot eyes and a "
              "small smile; indigo ink with a cool grey rim. " + STYLE),
    "ink-b": ("A plump ink drop sitting in a shallow round inkwell, the drop's face peeking over the rim; "
              "tiny dot eyes, no limbs. " + STYLE),
    "nib": ("A rounded calligraphy pen nib character standing upright, a soft heart-shaped nib body with a slit, "
            "tiny dot eyes on the nib, no arms. " + STYLE),
    "stamp": ("A chunky rounded stamp/seal character with a soft handle and a wide base, tiny dot eyes on the base, "
              "a small carved imprint pattern of simple dots, no letters. " + STYLE),
    "layers": ("A character made of three stacked translucent rounded sheets, slightly offset, with tiny dot eyes on "
               "the front sheet and a small smile; indigo with cool grey edges. " + STYLE),
    "knot": ("A free-choice character: a soft rounded loop of ribbon folded like an Arabic calligraphic knot, "
             "with a tiny dot eye pair and a small smile, no letters. " + STYLE),
}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    entries = []
    for name, prompt in CONCEPTS.items():
        raw, usage = image_generate(prompt, size="1024x1536")
        cost = (usage.images or 1) * 0.01
        record_spend(f"mascot concept {name}", cost, kind="image")
        image = Image.open(io.BytesIO(raw)).convert("RGB")
        path = OUT / f"{name}.png"
        image.save(path)
        entries.append(
            {
                "name": name,
                "category": name,
                "prompt": prompt,
                "file": str(path),
                "cost_usd": round(cost, 4),
                "width": image.width,
                "height": image.height,
            }
        )
        print("generated", name, f"${cost:.2f}")
    (REPO / "docs").mkdir(exist_ok=True)
    MANIFEST.write_text(json.dumps({"concepts": entries}, indent=2, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
