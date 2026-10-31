"""Generate 8 demo-v4 pages where Muse Image renders the English lettering (2 variants each).

Criteria (checked before any live run): requested English must be spelled exactly, fully
visible, no extra text/watermarks; flat style; 2-4 regions; no digits or curves.
"""

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
OUT = REPO / "fixtures" / "demo-v4"
PAGES = OUT / "pages"
STYLE = (
    "Flat vector illustration, solid colour fills only, thick dark outlines, limited palette "
    "of cream, teal, terracotta and mustard, no gradients, no texture, no watermark, portrait 2:3."
)

SPECS = {
    "comic-a": ("A simple bakery counter with a baker, three empty speech bubbles and one empty caption banner. "
                "Inside the first bubble the exact English words FRESH BREAD?; inside the second EVERY MORNING; "
                "inside the third IS THAT YOU?; inside the caption box CHAPTER ONE. No other text. " + STYLE,
                ["FRESH BREAD?", "EVERY MORNING", "IS THAT YOU?", "CHAPTER ONE"]),
    "comic-b": ("A simple bakery counter with a baker, three empty speech bubbles. Inside them the exact English words "
                "BAKED TODAY, SMELLS GOOD, SAVE ME ONE. No other text. " + STYLE,
                ["BAKED TODAY", "SMELLS GOOD", "SAVE ME ONE"]),
    "shop-a": ("A simple bread shop poster with a loaf and wheat, one large empty panel. Inside it the exact English words "
               "THE BREAD BOX and OPEN EVERY DAY. No other text. " + STYLE,
               ["THE BREAD BOX", "OPEN EVERY DAY"]),
    "shop-b": ("A simple cafe poster with a cup and a plant, one large empty panel. Inside it the exact English words "
               "THE COFFEE CORNER and FRESH PASTRIES. No other text. " + STYLE,
               ["THE COFFEE CORNER", "FRESH PASTRIES"]),
    "label-a": ("A simple honey jar with a blank cream label. On the label the exact English words WILDFLOWER HONEY and "
                "SMALL BATCH. No other text. " + STYLE,
                ["WILDFLOWER HONEY", "SMALL BATCH"]),
    "label-b": ("A simple honey jar with a blank cream label. On the label the exact English words GOLDEN HONEY and "
                "PURE AND SIMPLE. No other text. " + STYLE,
                ["GOLDEN HONEY", "PURE AND SIMPLE"]),
    "postcard-a": ("A simple seaside postcard with a lighthouse, one large white panel. Inside it the exact English words "
                   "SEASIDE POSTCARD and WISH YOU WERE HERE. No other text. " + STYLE,
                   ["SEASIDE POSTCARD", "WISH YOU WERE HERE"]),
    "postcard-b": ("A simple mountain postcard with hills, one large white panel. Inside it the exact English words "
                   "MOUNTAIN POSTCARD and GREETINGS FROM THE HILLS. No other text. " + STYLE,
                   ["MOUNTAIN POSTCARD", "GREETINGS FROM THE HILLS"]),
}


def main() -> None:
    PAGES.mkdir(parents=True, exist_ok=True)
    manifest = []
    for name, (prompt, texts) in SPECS.items():
        raw, usage = image_generate(prompt, size="1024x1536")
        record_spend(f"demo-v4 image {name}", (usage.images or 1) * 0.01, kind="image")
        image = Image.open(io.BytesIO(raw)).convert("RGB").resize((1280, 1920), Image.LANCZOS)
        image.save(PAGES / f"{name}.jpg", "JPEG", quality=90, optimize=True)
        manifest.append(
            {
                "id": name,
                "image": f"pages/{name}.jpg",
                "requested_texts": texts,
                "expected_texts": texts,
                "note": "model-rendered text; actual transcription pending",
                "prompt": prompt,
            }
        )
        print("generated", name)
    (OUT / "manifest.json").write_text(json.dumps({"pages": manifest}, indent=2, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
