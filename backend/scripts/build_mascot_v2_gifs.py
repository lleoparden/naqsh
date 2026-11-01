"""Animated GIF previews from the 12 fps state frames."""

from __future__ import annotations

from pathlib import Path

from PIL import Image

ROOT = Path(r"L:\naqsh-review\mascot-assets\v2")
FRAMES = ROOT / "frames" / "12fps"
OUT = ROOT / "previews" / "gif"
STATES = ["idle", "blink", "talking", "thinking", "curious", "surprised", "confused", "happy", "excited", "laughing", "proud", "sad", "sleepy", "wave-hello", "wave-goodbye", "working"]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for state in STATES:
        frames = []
        for path in sorted((FRAMES / state).glob("frame-*.png")):
            image = Image.open(path).convert("RGBA")
            image.thumbnail((384, 384), Image.LANCZOS)
            canvas = Image.new("RGBA", (384, 384), (27, 27, 31, 255))
            canvas.alpha_composite(image, ((384 - image.width) // 2, (384 - image.height) // 2))
            frames.append(canvas.convert("P", palette=Image.ADAPTIVE, colors=128))
        frames[0].save(OUT / f"{state}.gif", save_all=True, append_images=frames[1:], duration=83, loop=0, optimize=True)
        print(state, len(frames))


if __name__ == "__main__":
    main()
