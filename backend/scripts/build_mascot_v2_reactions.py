"""Build the 12+ reaction clips from v2 state frames, plus equivalent gesture clips."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

from PIL import Image

import imageio_ffmpeg

ROOT = Path(r"L:\naqsh-review\mascot-assets\v2")
FRAMES = ROOT / "frames" / "24fps"
OUT = ROOT / "reactions"
VIDEO = ROOT / "reaction-clips"
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()

COPY = {
    "shake": "confused",
    "shrug": "proud",
    "thumbs-up": "proud",
    "thinking-loop": "thinking",
    "loading-loop": "working",
    "success-pop": "excited",
    "error-shake": "confused",
    "wave-hello": "wave-hello",
    "wave-goodbye": "wave-goodbye",
    "surprise": "surprised",
}


def save_sequence(name: str, images: list[Image.Image]) -> Path:
    folder = OUT / name
    folder.mkdir(parents=True, exist_ok=True)
    for index, image in enumerate(images):
        image.save(folder / f"frame-{index:03d}.png")
    return folder


def custom(name: str, mode: str) -> Path:
    base = Image.open(FRAMES / "idle" / "frame-000.png").convert("RGBA")
    images = []
    frames = 24
    for index in range(frames):
        p = index / (frames - 1)
        if mode == "nod":
            image = base.copy()
            dy = -5 * (1 - abs(2 * p - 1)) ** 2
            image = image.transform(image.size, Image.AFFINE, (1, 0, 0, 0, 1, -dy), resample=Image.BICUBIC)
        elif mode == "lean-left":
            image = base.rotate(9 * (1 - abs(2 * p - 1)) ** 2, resample=Image.BICUBIC, translate=(-6 * p, 0), fillcolor=(0, 0, 0, 0))
        else:
            image = base.rotate(-9 * (1 - abs(2 * p - 1)) ** 2, resample=Image.BICUBIC, translate=(6 * p, 0), fillcolor=(0, 0, 0, 0))
        images.append(image)
    return save_sequence(name, images)


def copy_state(name: str, state: str) -> Path:
    folder = OUT / name
    if folder.exists():
        shutil.rmtree(folder)
    shutil.copytree(FRAMES / state, folder)
    for seam in folder.glob("seam.png"):
        seam.unlink()
    return folder


def encode(src: Path, name: str) -> dict:
    VIDEO.mkdir(parents=True, exist_ok=True)
    webm = VIDEO / f"{name}-768-24fps-alpha.webm"
    prores = VIDEO / f"{name}-768-24fps-prores4444.mov"
    subprocess.run([FFMPEG, "-y", "-hide_banner", "-loglevel", "error", "-framerate", "24", "-i", str(src / "frame-%03d.png"), "-c:v", "libvpx-vp9", "-pix_fmt", "yuva420p", "-auto-alt-ref", "0", "-b:v", "0", "-crf", "28", "-metadata:s:v:0", "alpha_mode=1", str(webm)], check=True)
    subprocess.run([FFMPEG, "-y", "-hide_banner", "-loglevel", "error", "-framerate", "24", "-i", str(src / "frame-%03d.png"), "-c:v", "prores_ks", "-profile:v", "4444", "-pix_fmt", "yuva444p10le", str(prores)], check=True)
    return {"name": name, "frames": len(list(src.glob("frame-*.png"))), "webm": str(webm), "prores": str(prores)}


def main() -> None:
    entries = []
    for name, mode in (("nod", "nod"), ("point-left", "lean-left"), ("point-right", "lean-right")):
        entries.append(encode(custom(name, mode), name))
    for name, state in COPY.items():
        entries.append(encode(copy_state(name, state), name))
    (ROOT / "reactions.json").write_text(json.dumps(entries, indent=2), encoding="utf-8")
    print(f"{len(entries)} reaction clips")


if __name__ == "__main__":
    main()
