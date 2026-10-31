"""Generate 5 polished demo candidate pages, run each live once, build a contact sheet.

Sources and results stay outside the repo (L:\\naqsh-review\\demo-candidates\\); only the
script and a manifest are committed. Requires a LIVE_MODE=1 server on port 8001.
"""

from __future__ import annotations

import io
import json
import sys
from pathlib import Path

import requests
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.pipeline.meta import image_generate
from app.pipeline.spend import record_spend

REPO = Path(__file__).resolve().parents[2]
OUT = Path(r"L:\naqsh-review\demo-candidates")
SOURCES = OUT / "sources"
RESULTS = OUT / "results"
FONT = REPO / "assets" / "fonts" / "Inter-Variable.ttf"
API = "http://127.0.0.1:8001"
SIZE = (1280, 1920)

PAGES = {
    "comic-bakery": {
        "prompt": "Flat vector comic page, original artwork: bakery counter at dusk, three EMPTY speech bubbles and one EMPTY caption banner, cream/teal/terracotta, no lettering, no text, portrait.",
        "texts": [
            ("FRESH BREAD?", [100, 200, 560, 380], 64),
            ("EVERY MORNING", [690, 340, 1200, 520], 56),
            ("SOLD OUT", [360, 1040, 920, 1200], 68),
            ("CHAPTER ONE", [200, 90, 1080, 190], 52),
        ],
    },
    "bakery-poster": {
        "prompt": "Warm flat-vector bakery poster background, original artwork: wheat, bread and a sun, large empty area at the top, no lettering, no text, portrait.",
        "texts": [
            ("BAKERY OPEN", [80, 200, 1200, 460], 96),
            ("FRESH LOAVES", [140, 1500, 1140, 1650], 52),
            ("07:00 - 19:00", [140, 1680, 1140, 1800], 48),
        ],
    },
    "cafe-menu": {
        "prompt": "Printed cafe menu paper texture, original artwork: cream paper, thin border, empty columns, no lettering, no text, portrait.",
        "texts": [
            ("CAFE MENU", [180, 120, 1100, 260], 64),
            ("ESPRESSO 3.50", [120, 380, 1160, 480], 44),
            ("FLAT WHITE 4.25", [120, 540, 1160, 640], 44),
            ("CROISSANT 3.00", [120, 700, 1160, 800], 44),
            ("OPEN 08:00 - 18:00", [120, 1500, 1160, 1620], 40),
        ],
    },
    "honey-label": {
        "prompt": "Flat vector product label illustration, original artwork: honey jar on a wooden table, blank cream label, warm light, no lettering, no text, portrait.",
        "texts": [
            ("WILDFLOWER", [250, 780, 1030, 880], 48),
            ("HONEY", [250, 920, 1030, 1040], 64),
            ("500g", [250, 1080, 1030, 1180], 44),
            ("12.00", [250, 1220, 1030, 1320], 44),
        ],
    },
    "night-market": {
        "prompt": "Retro travel poster background, original artwork: night market with lanterns, large empty sky area, no lettering, no text, portrait.",
        "texts": [
            ("NIGHT MARKET", [80, 200, 1200, 440], 88),
            ("FRIDAY 18:00", [220, 1500, 1060, 1620], 48),
            ("FREE ENTRY", [220, 1660, 1060, 1780], 48),
        ],
    },
}


def font(size: int):
    return ImageFont.truetype(str(FONT), size)


def draw_text(image: Image.Image, text: str, box, size: int) -> None:
    draw = ImageDraw.Draw(image)
    f = font(size)
    width = draw.textbbox((0, 0), text, font=f)[2]
    x = box[0] + (box[2] - box[0] - width) // 2
    y = box[1] + (box[3] - box[1] - size) // 2
    draw.text((x, y), text, font=f, fill=(24, 20, 16))


def main() -> None:
    SOURCES.mkdir(parents=True, exist_ok=True)
    RESULTS.mkdir(parents=True, exist_ok=True)
    manifest = []
    for name, spec in PAGES.items():
        raw, usage = image_generate(spec["prompt"], size="1024x1536")
        record_spend(f"demo candidate image {name}", (usage.images or 1) * 0.01, kind="image")
        image = Image.open(io.BytesIO(raw)).convert("RGB").resize(SIZE, Image.LANCZOS)
        for text, box, size in spec["texts"]:
            draw_text(image, text, box, size)
        source = SOURCES / f"{name}.jpg"
        image.save(source, "JPEG", quality=90, optimize=True)

        with source.open("rb") as handle:
            response = requests.post(
                f"{API}/api/localize",
                files={"image": (source.name, handle, "image/jpeg")},
                data={"register": "egyptian", "background_layers": "true"},
                timeout=600,
            )
        response.raise_for_status()
        receipt = response.json()
        result = requests.get(f"{API}/api/jobs/{receipt['id']}/files/output.png", timeout=120)
        result.raise_for_status()
        (RESULTS / f"{name}.png").write_bytes(result.content)
        manifest.append(
            {
                "id": name,
                "source": str(source),
                "result": str(RESULTS / f"{name}.png"),
                "regions": len(receipt.get("regions") or []),
                "seconds": round((receipt.get("total_ms") or 0) / 1000, 1),
                "cost_usd": round(receipt.get("total_cost_usd") or 0, 4),
                "prompt": spec["prompt"],
            }
        )
        print(name, manifest[-1]["regions"], manifest[-1]["seconds"], manifest[-1]["cost_usd"])

    thumb_w = 420
    rows = []
    for item in manifest:
        src = Image.open(item["source"]).convert("RGB")
        res = Image.open(item["result"]).convert("RGB")
        thumb_h = int(src.height * thumb_w / src.width)
        rows.append((src.resize((thumb_w, thumb_h)), res.resize((thumb_w, thumb_h)), item))
    sheet = Image.new("RGB", (thumb_w * 2 + 90, (rows[0][0].height + 70) * len(rows) + 20), "white")
    draw = ImageDraw.Draw(sheet)
    label_font = font(22)
    for index, (src, res, item) in enumerate(rows):
        y = 20 + index * (src.height + 70)
        sheet.paste(src, (20, y))
        sheet.paste(res, (thumb_w + 60, y))
        draw.text((20, y + src.height + 8), f"{item['id']} — {item['regions']} regions, {item['seconds']}s, ${item['cost_usd']:.4f}", font=label_font, fill=(20, 20, 20))
    sheet.save(OUT / "contact-sheet.jpg", "JPEG", quality=90)
    (REPO / "docs" / "evidence" / "demo-candidates.json").write_text(
        json.dumps({"candidates": manifest}, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print("contact sheet", OUT / "contact-sheet.jpg")


if __name__ == "__main__":
    main()
