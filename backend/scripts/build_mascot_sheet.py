"""Large labeled mascot contact sheet outside the repo."""

from pathlib import Path

import json
from PIL import Image, ImageDraw, ImageFont

REPO = Path(__file__).resolve().parents[2]
MANIFEST = json.loads((REPO / "docs" / "mascot-manifest.json").read_text(encoding="utf-8"))
OUT = Path(r"L:\naqsh-review\mascot\contact-sheet.jpg")
FONT = REPO / "assets" / "fonts" / "Inter-Variable.ttf"


def font(size):
    return ImageFont.truetype(str(FONT), size)


def grid(entries, title, y):
    cell = 420
    cols = 5
    rows = (len(entries) + cols - 1) // cols
    canvas = Image.new("RGB", (cols * (cell + 20) + 20, y + rows * (cell + 55) + 20), "white")
    draw = ImageDraw.Draw(canvas)
    draw.text((20, 20), title, font=font(30), fill=(0, 0, 0))
    for index, entry in enumerate(entries):
        image = Image.open(entry["file"]).convert("RGB")
        image.thumbnail((cell, cell), Image.LANCZOS)
        col, row = index % cols, index // cols
        x = 20 + col * (cell + 20)
        yy = y + row * (cell + 55)
        canvas.paste(image, (x, yy))
        label = entry.get("name") or f"{entry['base']} — {entry['state']}"
        draw.text((x, yy + cell + 4), label, font=font(20), fill=(0, 0, 0))
    return canvas


concepts = grid(MANIFEST["concepts"], "Concepts (8)", 60)
expressions = grid(MANIFEST["expressions"], "Expressions (3 concepts x 3 states)", 60)
width = max(concepts.width, expressions.width)
sheet = Image.new("RGB", (width, concepts.height + expressions.height), "white")
sheet.paste(concepts, (0, 0))
sheet.paste(expressions, (0, concepts.height))
sheet.save(OUT, "JPEG", quality=92)
print(OUT, sheet.size)
