"""Generate 10-frame crossfade transitions between idle and each state."""

from __future__ import annotations

from pathlib import Path

from PIL import Image

ROOT = Path(r"L:\naqsh-review\mascot-assets\v2\frames")
STATES = ["talking", "blink", "thinking", "curious", "surprised", "confused", "happy", "excited", "laughing", "proud", "sad", "sleepy", "wave-hello", "wave-goodbye", "working"]
FRAMES = 10


def pick(state: str) -> Image.Image:
    folder = ROOT / "24fps" / state
    frames = sorted(folder.glob("frame-*.png"))
    index = 0 if state == "talking" else len(frames) // 2
    return Image.open(frames[index]).convert("RGBA")


def blend(a: Image.Image, b: Image.Image, t: float) -> Image.Image:
    return Image.blend(a, b, t)


def main() -> None:
    idle = pick("idle")
    for state in STATES:
        other = pick(state)
        for direction, start, end in (("to", idle, other), ("from", other, idle)):
            name = f"idle-to-{state}" if direction == "to" else f"{state}-to-idle"
            out = ROOT / "transitions" / name
            out.mkdir(parents=True, exist_ok=True)
            for index in range(FRAMES):
                t = index / (FRAMES - 1)
                blend(start, end, t).save(out / f"frame-{index:03d}.png")
        print(state, "transitions")


if __name__ == "__main__":
    main()
