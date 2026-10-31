"""Demo candidates v2: flat-vector backgrounds, code-drawn text containers and English text.

Six pages, 2-4 large regions, no digits/prices/curves. Text is drawn inside plain
bubbles/panels so ground truth is exact and the background behind text is flat.
"""

from __future__ import annotations

import io
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.pipeline.meta import image_generate
from app.pipeline.spend import record_spend

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "fixtures" / "demo-v2"
PAGES = OUT / "pages"
FONT_PATH = REPO / "assets" / "fonts" / "Inter-Variable.ttf"
SIZE = (1280, 1920)
INK = (24, 20, 16)
PAPER = (250, 244, 228)

STYLE = (
    "Flat vector illustration, solid colour fills only, thick dark outlines, limited palette "
    "of cream, teal, terracotta and mustard, no gradients, no texture, no shading, no lettering, "
    "no text, no logos, no watermark, portrait 2:3."
)

PAGES_SPEC = {
    "comic-bakery-flat": {
        "prompt": "A simple bakery counter with a baker, bread shelves and lamps. " + STYLE,
        "containers": [
            ("bubble", [70, 120, 590, 420]),
            ("bubble", [660, 260, 1210, 560]),
            ("bubble", [260, 1180, 900, 1460]),
            ("banner", [180, 40, 1100, 150]),
        ],
        "texts": ["FRESH BREAD?", "EVERY MORNING", "IS THAT YOU?", "CHAPTER ONE"],
        "features": ["3 speech bubbles", "caption banner"],
    },
    "cafe-poster-flat": {
        "prompt": "A simple cafe storefront with an awning, a cup and a plant. " + STYLE,
        "containers": [
            ("panel", [100, 180, 1180, 480]),
            ("panel", [180, 1480, 1100, 1680]),
        ],
        "texts": ["THE COFFEE CORNER", "OPEN EVERY DAY"],
        "features": ["large title", "small subtitle"],
    },
    "honey-label-flat": {
        "prompt": "A simple honey jar on a wooden table, blank label area, wheat stems. " + STYLE,
        "containers": [("panel", [280, 760, 1000, 1280])],
        "texts": ["WILDFLOWER\nHONEY\nSMALL BATCH"],
        "features": ["product label"],
    },
    "chalkboard-flat": {
        "prompt": "A simple dark chalkboard with a wooden frame, empty centre. " + STYLE,
        "containers": [],
        "texts": ["TODAY'S BREAD\nSOURDOUGH\nRYE"],
        "features": ["chalkboard", "3 lines"],
        "chalk": True,
    },
    "postcard-flat": {
        "prompt": "A simple seaside landscape with a lighthouse and gulls, large calm sky. " + STYLE,
        "containers": [("panel", [120, 200, 1160, 620]), ("panel", [220, 1500, 1060, 1680])],
        "texts": ["SEASIDE POSTCARD", "WISH YOU WERE HERE"],
        "features": ["travel postcard"],
    },
    "children-flat": {
        "prompt": "A simple friendly rabbit in a meadow with flowers, two large plain sky areas. " + STYLE,
        "containers": [("bubble", [80, 140, 640, 460]), ("bubble", [640, 360, 1200, 680])],
        "texts": ["LET'S GO OUTSIDE!", "WAIT FOR ME!"],
        "features": ["children's book", "2 bubbles"],
    },
}


def font(size: int) -> ImageFont.FreeTypeFont:
    f = ImageFont.truetype(str(FONT_PATH), size)
    try:
        f.set_variation_by_name("Bold")
    except Exception:
        pass
    return f


def _text(draw, text: str, box, size: int, fill=INK, align="center") -> None:
    x1, y1, x2, y2 = box
    f = font(size)
    lines = text.split("\n")
    heights = [draw.textbbox((0, 0), line, font=f)[3] for line in lines]
    total = sum(heights) + (len(lines) - 1) * int(size * 0.2)
    y = y1 + (y2 - y1 - total) // 2
    for line, h in zip(lines, heights):
        width = draw.textbbox((0, 0), line, font=f)[2]
        x = x1 + (x2 - x1 - width) // 2 if align == "center" else x1
        draw.text((x, y), line, font=f, fill=fill)
        y += h + int(size * 0.2)


def main() -> None:
    PAGES.mkdir(parents=True, exist_ok=True)
    manifest = []
    for name, spec in PAGES_SPEC.items():
        raw, usage = image_generate(spec["prompt"], size="1024x1536")
        record_spend(f"demo-v2 image {name}", (usage.images or 1) * 0.01, kind="image")
        image = Image.open(io.BytesIO(raw)).convert("RGB").resize(SIZE, Image.LANCZOS)
        draw = ImageDraw.Draw(image)
        for (kind, box), text in zip(spec["containers"], spec["texts"]):
            if kind == "bubble":
                draw.rounded_rectangle(box, radius=90, fill=PAPER, outline=INK, width=7)
            elif kind == "banner":
                draw.rectangle(box, fill=PAPER, outline=INK, width=6)
            elif kind == "panel":
                draw.rounded_rectangle(box, radius=24, fill=PAPER, outline=INK, width=6)
        if spec.get("chalk"):
            _text(draw, spec["texts"][0], [120, 260, 1160, 1660], 96, fill=(245, 245, 235))
        else:
            # Draw text into the containers; for panels, the first container gets all lines.
            if spec["containers"]:
                for (kind, box), text in zip(spec["containers"], spec["texts"]):
                    _text(draw, text, box, 84 if len(text) < 20 else 64)
        path = PAGES / f"{name}.jpg"
        image.save(path, "JPEG", quality=90, optimize=True)
        boxes = [
            {"id": f"t{index + 1}", "type": "dialogue" if kind == "bubble" else "signage", "box": box, "text": text.replace("\n", " ")}
            for index, ((kind, box), text) in enumerate(zip(spec["containers"], spec["texts"]))
        ] if spec["containers"] else [
            {"id": "t1", "type": "signage", "box": [120, 260, 1160, 1660], "text": spec["texts"][0].replace("\n", " ")}
        ]
        if spec.get("chalk"):
            boxes = [
                {"id": f"t{index + 1}", "type": "signage", "box": [120, 260 + index * 440, 1160, 640 + index * 440], "text": line}
                for index, line in enumerate(spec["texts"][0].split("\n"))
            ]
        manifest.append(
            {
                "id": name,
                "image": f"pages/{name}.jpg",
                "expected": "pass",
                "features": spec["features"],
                "regions": boxes,
                "generator": {"images": "muse-image-1.0", "text": "code-drawn Inter Bold", "prompt": spec["prompt"]},
            }
        )
        print("built", name, len(boxes))
    (OUT / "manifest.json").write_text(json.dumps({"pages": manifest}, indent=2, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
