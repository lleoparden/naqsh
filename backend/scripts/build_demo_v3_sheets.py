"""Build the two v3 contact sheets outside the repo: originals-only and original|result."""

from pathlib import Path

import json
from PIL import Image, ImageDraw, ImageFont

REPO = Path(__file__).resolve().parents[2]
SRC = Path(r"L:\naqsh-review\demo-v3\sources")
RES = Path(r"L:\naqsh-review\demo-v3\results")
OUT = Path(r"L:\naqsh-review\demo-v3")
FONT = REPO / "assets" / "fonts" / "Inter-Variable.ttf"
SUMMARY = json.loads((REPO / "docs" / "evidence" / "demo-v3" / "summary.json").read_text(encoding="utf-8"))["posters"]


def font(size: int):
    return ImageFont.truetype(str(FONT), size)


def sheet(items, path, title):
    width = 760
    rows = []
    for src, res, label in items:
        src_img = Image.open(src).convert("RGB")
        h = int(src_img.height * width / src_img.width)
        res_img = Image.open(res).convert("RGB").resize((width, h), Image.LANCZOS) if res else None
        rows.append((src_img.resize((width, h), Image.LANCZOS), res_img, label))
    row_h = rows[0][0].height
    canvas = Image.new("RGB", (width * (2 if rows[0][1] else 1) + 80, 80 + (row_h + 90) * len(rows)), "white")
    draw = ImageDraw.Draw(canvas)
    draw.text((20, 20), title, font=font(30), fill=(0, 0, 0))
    for index, (src_img, res_img, label) in enumerate(rows):
        y = 80 + index * (row_h + 90)
        canvas.paste(src_img, (20, y))
        if res_img:
            canvas.paste(res_img, (width + 60, y))
        draw.text((20, y + row_h + 8), label, font=font(22), fill=(0, 0, 0))
    canvas.save(path, "JPEG", quality=90)
    print(path, canvas.size)


originals = []
results = []
for row in SUMMARY:
    source = next(p for p in SRC.iterdir() if p.name == row["file"])
    label = f"{source.stem[:48]} — PD (LoC/Wikimedia)"
    originals.append((source, None, label))
    results.append(
        (
            source,
            row["result"],
            f"{source.stem[:40]} — {row['text_layers']} text, {row['seconds']} s, ${row['cost_usd']:.4f}, verify flags ghost text",
        )
    )

sheet(originals, OUT / "originals-sheet.jpg", "Demo sources v3 — originals only (public domain)")
sheet(results, OUT / "results-sheet.jpg", "Demo sources v3 — original | result")
