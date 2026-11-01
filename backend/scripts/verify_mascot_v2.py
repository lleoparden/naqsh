"""Verify v2 frame counts and loop seams; build the labeled key-frame contact sheet."""

from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFont

ROOT = Path(r"L:\naqsh-review\mascot-assets\v2")
FRAMES = ROOT / "frames"
LOOPS = ["idle", "talking", "thinking", "laughing", "sleepy", "working"]
STATES = LOOPS + [
    "blink", "curious", "surprised", "confused", "happy", "excited", "proud", "sad", "wave-hello", "wave-goodbye",
]
FONT = Path(r"L:\naqsh\assets\fonts\Inter-Variable.ttf")


def check(fps: int) -> dict:
    report = {}
    for state in STATES:
        folder = FRAMES / f"{fps}fps" / state
        count = len(list(folder.glob("frame-*.png")))
        entry = {"frames": count, "loop": state in LOOPS}
        if state in LOOPS:
            first = Image.open(folder / "frame-000.png").convert("RGBA")
            seam = Image.open(folder / "seam.png").convert("RGBA")
            diff = ImageChops.difference(first, seam)
            entry["seam_identical"] = diff.getbbox() is None
            entry["seam_max_channel_diff"] = max(value[1] for value in diff.getextrema())
        report[state] = entry
    return report


def sheet(fps: int) -> None:
    cell, cols = 260, 4
    rows = (len(STATES) + cols - 1) // cols
    canvas = Image.new("RGB", (cols * (cell + 16) + 16, rows * (cell + 48) + 16), "white")
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.truetype(str(FONT), 18)
    small = ImageFont.truetype(str(FONT), 14)
    for index, state in enumerate(STATES):
        folder = FRAMES / f"{fps}fps" / state
        frames = sorted(folder.glob("frame-*.png"))
        image = Image.open(frames[len(frames) // 2]).convert("RGB")
        image.thumbnail((cell, cell), Image.LANCZOS)
        x = 16 + (index % cols) * (cell + 16)
        y = 16 + (index // cols) * (cell + 48)
        canvas.paste(image, (x, y))
        draw.text((x, y + cell + 2), state, font=font, fill=(0, 0, 0))
        draw.text((x, y + cell + 22), f"{len(frames)}f @ {fps}fps", font=small, fill=(90, 90, 90))
    out = ROOT / "previews" / f"contact-sheet-{fps}fps.jpg"
    out.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out, "JPEG", quality=92)
    print(out, canvas.size)


def main() -> None:
    report = {f"{fps}fps": check(fps) for fps in (24, 12)}
    (ROOT / "verification-frames.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    for fps in (24, 12):
        sheet(fps)
    print(json.dumps(report, indent=2)[:1200])


if __name__ == "__main__":
    main()
