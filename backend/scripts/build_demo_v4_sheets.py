"""Demo v4 contact sheets: originals-only and original|result, including WPA limits."""

from pathlib import Path

import json
from PIL import Image, ImageDraw, ImageFont

REPO = Path(__file__).resolve().parents[2]
V4 = REPO / "fixtures" / "demo-v4" / "pages"
V4_RES = Path(r"L:\naqsh-review\demo-v4\results")
V3_SRC = Path(r"L:\naqsh-review\demo-v3\sources")
V3_RES = Path(r"L:\naqsh-review\demo-v3\results")
OUT = Path(r"L:\naqsh-review\demo-v4")
FONT = REPO / "assets" / "fonts" / "Inter-Variable.ttf"
V4_SUM = json.loads((REPO / "docs" / "evidence" / "demo-v4" / "summary.json").read_text(encoding="utf-8"))["pages"]
V3_SUM = json.loads((REPO / "docs" / "evidence" / "demo-v3" / "summary.json").read_text(encoding="utf-8"))["posters"]


def font(size):
    return ImageFont.truetype(str(FONT), size)


def build(rows, path, title, two_up):
    width = 760
    items = []
    for source, result, label in rows:
        src = Image.open(source).convert("RGB")
        h = int(src.height * width / src.width)
        res = Image.open(result).convert("RGB").resize((width, h), Image.LANCZOS) if result and Path(result).exists() else None
        items.append((src.resize((width, h), Image.LANCZOS), res, label))
    row_h = items[0][0].height
    canvas = Image.new("RGB", (width * (2 if two_up else 1) + 80, 90 + (row_h + 80) * len(items)), "white")
    draw = ImageDraw.Draw(canvas)
    draw.text((20, 20), title, font=font(28), fill=(0, 0, 0))
    for index, (src, res, label) in enumerate(items):
        y = 90 + index * (row_h + 80)
        canvas.paste(src, (20, y))
        if res:
            canvas.paste(res, (width + 60, y))
        draw.text((20, y + row_h + 8), label, font=font(20), fill=(0, 0, 0))
    canvas.save(path, "JPEG", quality=90)
    print(path, canvas.size)


originals, results = [], []
for row in V4_SUM:
    source = V4 / f"{row['id']}.jpg" if row["id"] != "phase1-baker" else REPO / "assets" / "generated" / "test-panel.png"
    label = f"{row['id']} — Muse-rendered English"
    originals.append((source, None, label))
    results.append((source, row["result"], f"{row['id']} — recall {row['recall']}, {row['seconds']} s, ${row['cost_usd']:.4f}, bubbles {row['bubbles']}"))

for row in V3_SUM:
    source = next(p for p in V3_SRC.iterdir() if p.name == row["file"])
    preferred = " (owner preferred)" if "Zion" in row["file"] else ""
    label = f"{source.stem[:44]} — limits candidate{preferred}; no rerun"
    originals.append((source, None, label))
    results.append((source, row["result"], f"{source.stem[:44]} — limits candidate{preferred}; {row['seconds']} s, ${row['cost_usd']:.4f}"))

build(originals, OUT / "originals-sheet.jpg", "Demo v4 — originals only (Muse text + PD limits)", False)
build(results, OUT / "results-sheet.jpg", "Demo v4 — original | result", True)
