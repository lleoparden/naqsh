"""Build the English test suite: Muse Image artwork + code-drawn English text.

Ten text-free pages get exact ground truth drawn in code; three pages let Muse Image
render the text (expected-fail cases: curved, photo label, handwriting) and are
transcribed by hand in the manifest.

Run: python backend/scripts/build_test_suite.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.pipeline.meta import image_generate
from app.pipeline.spend import record_spend

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "fixtures" / "test-suite"
PAGES = OUT / "pages"
FONT = REPO / "assets" / "fonts" / "Inter-Variable.ttf"
SIZE = (1280, 1920)

TEXT_FREE = {
    "comic-three-bubbles": "Flat vector comic panel, original artwork: a bakery counter at dusk, a young baker, warm lamps, three EMPTY speech bubbles with thick black outlines (left, right, lower middle), cream/teal/terracotta palette, no lettering, no text, no logos, no signature, portrait.",
    "comic-thought-caption": "Flat vector comic panel, original artwork: a baker thinking at a window, one EMPTY cloud-shaped thought bubble in the middle and one EMPTY rectangular caption banner at the top, no lettering, no text, no logos, portrait.",
    "comic-sfx": "Flat vector comic action panel, original artwork: a tray of bread falling, an EMPTY jagged explosion shape on the right, motion lines, no lettering, no text, no logos, portrait.",
    "crowded-shelf": "Flat vector illustration of a dense bakery shelf with many breads, jars, cakes and small price tags, all tags EMPTY, no lettering, no text, no logos, portrait.",
    "tiny-hours": "Flat vector poster background, original artwork: a small bakery facade, large empty sign area at the top, pale paper, no lettering, no text, no logos, portrait.",
    "poster-title": "Retro travel poster background, original artwork: a night market with lanterns, large empty sky area at the top for a headline, no lettering, no text, no logos, portrait.",
    "poster-lowcontrast": "Retro travel poster background in pale low-contrast pastel tones, night market with lanterns, large empty sky area, no lettering, no text, no logos, portrait.",
    "menu-prices": "Printed menu paper texture, original artwork: cream paper with faint stains and a thin border, empty columns, no lettering, no text, no logos, portrait.",
    "chalkboard": "Dark green chalkboard texture, original artwork: wooden frame, faint chalk dust, completely empty centre, no lettering, no text, no logos, portrait.",
    "no-text": "Still life illustration, original artwork: bread basket, jam jar and wheat on a table, warm light, no lettering, no text, no labels, no logos, portrait.",
}

MODEL_TEXT = {
    "poster-curved": "Retro travel poster, original artwork: a sunset over dunes, and a large CURVED headline in English reading exactly 'SUNSET TOURS', no other text, no logos, no real brands, portrait.",
    "label-photo": "Photo-like product shot, original artwork: a honey jar on a wooden table, label with handwritten English text reading exactly 'WILDFLOWER HONEY 500g', no other text, no logos, no real brands, portrait.",
    "sign-handwriting": "Chalkboard sign, original artwork: handwritten English text in chalk reading exactly 'FRESH BREAD DAILY', no other text, no logos, no real brands, portrait.",
}


def font(size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONT), size)


def draw_box(draw, text: str, box, size: int, color=(20, 17, 15), align="center") -> None:
    x1, y1, x2, y2 = box
    f = font(size)
    lines = text.split("\n")
    heights = [draw.textbbox((0, 0), line, font=f)[3] for line in lines]
    total = sum(heights) + (len(lines) - 1) * int(size * 0.25)
    y = y1 + (y2 - y1 - total) // 2
    for line, h in zip(lines, heights):
        width = draw.textbbox((0, 0), line, font=f)[2]
        x = x1 + (x2 - x1 - width) // 2 if align == "center" else x1
        draw.text((x, y), line, font=f, fill=color)
        y += h + int(size * 0.25)


def base(name: str, prompt: str) -> Image.Image:
    raw, usage = image_generate(prompt, size="1024x1536")
    cost = (usage.images or 1) * 0.01
    record_spend(f"test-suite image {name}", cost, kind="image")
    image = Image.open(__import__("io").BytesIO(raw)).convert("RGB").resize(SIZE, Image.LANCZOS)
    return image


def main() -> None:
    PAGES.mkdir(parents=True, exist_ok=True)
    entries = []

    # Code-drawn pass pages: (id, image, regions, features)
    specs = {
        "comic-three-bubbles": [
            ("b1", "dialogue", [90, 170, 560, 360], "FRESH BREAD?"),
            ("b2", "dialogue", [650, 300, 1180, 520], "EVERY MORNING"),
            ("b3", "dialogue", [300, 980, 900, 1180], "IS THAT YOU?"),
        ],
        "comic-thought-caption": [
            ("cap", "caption", [150, 100, 1130, 250], "CHAPTER ONE"),
            ("thought", "dialogue", [240, 560, 900, 860], "MAYBE MORE\nFLOUR?"),
        ],
        "comic-sfx": [
            ("sfx1", "sfx", [120, 250, 620, 520], "BOOM!"),
            ("sfx2", "sfx", [700, 900, 1180, 1150], "CRASH!"),
        ],
        "crowded-shelf": [
            (f"l{i}", "menu_item", [80 + (i % 3) * 390, 300 + (i // 3) * 380, 420 + (i % 3) * 390, 420 + (i // 3) * 380], t)
            for i, t in enumerate(
                ["RYE 4.50", "BAGUETTE 3.00", "SOURDOUGH 6.50", "BRIOCHE 5.00", "FOCACCIA 7.25", "PITA 2.75", "CAKE 8.00", "TARTS 9.50"]
            )
        ],
        "tiny-hours": [
            ("hours", "signage", [120, 240, 1160, 420], "OPENING HOURS\nMON-FRI 07:00 - 19:00\nSAT 08:00 - 16:00\nCLOSED SUNDAY"),
        ],
        "poster-title": [
            ("title", "signage", [80, 150, 1200, 450], "NIGHT MARKET"),
            ("sub", "signage", [200, 1600, 1080, 1760], "FRIDAY 18:00 · HALL 3 · FREE ENTRY"),
        ],
        "poster-lowcontrast": [
            ("title", "signage", [80, 150, 1200, 450], "NIGHT MARKET"),
            ("sub", "signage", [200, 1600, 1080, 1760], "FRIDAY 18:00 · HALL 3 · FREE ENTRY"),
        ],
        "menu-prices": [
            ("h", "signage", [300, 120, 980, 240], "TODAY'S MENU"),
            ("m1", "menu_item", [120, 340, 760, 430], "SOURDOUGH 6.50"),
            ("m2", "menu_item", [120, 470, 760, 560], "BRIOCHE 5.00"),
            ("m3", "price", [820, 340, 1180, 430], "1200"),
            ("m4", "price", [820, 470, 1180, 560], "145"),
            ("t1", "signage", [120, 1500, 760, 1590], "OPEN 08:30 - 19:45"),
            ("t2", "price", [820, 1500, 1180, 1590], "12.50"),
        ],
        "chalkboard": [
            ("ch1", "signage", [140, 300, 1140, 520], "TODAY'S LOAF"),
            ("ch2", "menu_item", [140, 700, 1140, 850], "SOURDOUGH 6.00"),
            ("ch3", "menu_item", [140, 950, 1140, 1100], "RYE 4.50"),
        ],
    }
    colors = {"poster-lowcontrast": (186, 186, 186)}

    for name, regions in specs.items():
        image = base(name, TEXT_FREE[name])
        draw = ImageDraw.Draw(image)
        color = colors.get(name, (20, 17, 15))
        for _rid, _kind, box, text in regions:
            size = 72 if (box[3] - box[1]) > 300 else 48
            draw_box(draw, text, box, size, color=color)
        path = PAGES / f"{name}.jpg"
        image.save(path, "JPEG", quality=88, optimize=True)
        entries.append(
            {
                "id": name,
                "image": f"pages/{name}.jpg",
                "expected": "pass",
                "features": [],
                "regions": [
                    {"id": rid, "type": kind, "box": box, "text": text.replace("\n", " ")}
                    for rid, kind, box, text in regions
                ],
                "generator": {"images": "muse-image-1.0", "text": "code-drawn Inter", "prompt": TEXT_FREE[name]},
            }
        )
        print("pass", name)

    # No-text page.
    image = base("no-text", TEXT_FREE["no-text"])
    image.save(PAGES / "no-text.jpg", "JPEG", quality=88, optimize=True)
    entries.append(
        {
            "id": "no-text",
            "image": "pages/no-text.jpg",
            "expected": "pass",
            "features": ["zero regions"],
            "regions": [],
            "generator": {"images": "muse-image-1.0", "text": "none", "prompt": TEXT_FREE["no-text"]},
        }
    )

    # Model-text pages: text transcribed by hand after generation (filled below).
    for name, prompt in MODEL_TEXT.items():
        image = base(name, prompt)
        image.save(PAGES / f"{name}.jpg", "JPEG", quality=88, optimize=True)
        entries.append(
            {
                "id": name,
                "image": f"pages/{name}.jpg",
                "expected": "fail",
                "features": [],
                "regions": [],
                "generator": {"images": "muse-image-1.0", "text": "muse-rendered", "prompt": prompt},
                "note": "model-rendered text; manual transcription pending",
            }
        )
        print("model", name)

    (OUT / "manifest.json").write_text(json.dumps({"pages": entries}, indent=2, ensure_ascii=False), encoding="utf-8")
    print("wrote", OUT / "manifest.json")


if __name__ == "__main__":
    main()
