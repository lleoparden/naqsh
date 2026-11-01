"""Longer reaction clips (2 s / 3 s) and idle<->reaction transition blends."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

from PIL import Image

import imageio_ffmpeg

ROOT = Path(r"L:\naqsh-review\mascot-assets\v2")
REACTIONS = ROOT / "reactions"
LONG = ROOT / "reactions-long"
TRANS = ROOT / "frames" / "reaction-transitions"
CLIPS = ROOT / "reaction-clips-long"
TCLIPS = ROOT / "reaction-transition-clips"
IDLE = ROOT / "frames" / "24fps" / "idle" / "frame-000.png"
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
LOOPS_3S = {"thinking-loop", "loading-loop"}
FRAMES_10 = 10


def load_frames(folder: Path) -> list[Image.Image]:
    return [Image.open(path).convert("RGBA") for path in sorted(folder.glob("frame-*.png"))]


def extend(name: str) -> list[Image.Image]:
    frames = load_frames(REACTIONS / name)
    target = 72 if name in LOOPS_3S else 48
    return [frames[index % len(frames)] for index in range(target)]


def save(frames: list[Image.Image], folder: Path) -> None:
    if folder.exists():
        shutil.rmtree(folder)
    folder.mkdir(parents=True)
    for index, image in enumerate(frames):
        image.save(folder / f"frame-{index:03d}.png")


def encode(folder: Path, out: Path, fps: int = 24) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    webm = out / f"{folder.name}-768-24fps-alpha.webm"
    prores = out / f"{folder.name}-768-24fps-prores4444.mov"
    subprocess.run([FFMPEG, "-y", "-hide_banner", "-loglevel", "error", "-framerate", str(fps), "-i", str(folder / "frame-%03d.png"), "-c:v", "libvpx-vp9", "-pix_fmt", "yuva420p", "-auto-alt-ref", "0", "-b:v", "0", "-crf", "28", "-metadata:s:v:0", "alpha_mode=1", str(webm)], check=True)
    subprocess.run([FFMPEG, "-y", "-hide_banner", "-loglevel", "error", "-framerate", str(fps), "-i", str(folder / "frame-%03d.png"), "-c:v", "prores_ks", "-profile:v", "4444", "-pix_fmt", "yuva444p10le", str(prores)], check=True)
    return {"name": folder.name, "frames": len(list(folder.glob("frame-*.png"))), "webm": str(webm), "prores": str(prores)}


def main() -> None:
    names = sorted(path.name for path in REACTIONS.iterdir() if path.is_dir())
    report = []
    for name in names:
        frames = extend(name)
        folder = LONG / name
        save(frames, folder)
        report.append(encode(folder, CLIPS, 24))
        start = frames[0]
        mid = frames[len(frames) // 2]
        idle = Image.open(IDLE).convert("RGBA")
        for direction, a, b in (("to", idle, mid), ("from", mid, idle)):
            tname = f"idle-to-{name}" if direction == "to" else f"{name}-to-idle"
            tdir = TRANS / tname
            tdir.mkdir(parents=True, exist_ok=True)
            for index in range(FRAMES_10):
                Image.blend(a, b, index / (FRAMES_10 - 1)).save(tdir / f"frame-{index:03d}.png")
            report.append(encode(tdir, TCLIPS, 24))
        print(name, len(frames))
    (ROOT / "reactions-long.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"{len(report)} reaction/long clips + transitions")


if __name__ == "__main__":
    main()
