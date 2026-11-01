"""Voice-driven mascot presenter.

Amplitude-driven, NOT true lip sync: the WAV's smoothed loudness selects one of five
mouth frames; silence closes the mouth. Adds deterministic blinks, breathing and sway.
Optional markers place reaction frames at timestamps.

Usage:
  python backend/scripts/mascot_presenter.py --audio voice.wav --out out.mov
  python backend/scripts/mascot_presenter.py --audio voice.wav --markers markers.json --out out.mov
"""

from __future__ import annotations

import argparse
import json
import math
import random
import subprocess
import tempfile
import wave
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
FRAMES = Path(r"L:\naqsh-review\mascot-assets\v2\frames\24fps")
OUT = Path(r"L:\naqsh-review\mascot-assets\v2\presenter")
FPS = 30
SIZE = 768
MOUTH_FRAMES = [0, 7, 14, 22, 29]  # 5 shapes from the talking loop


def read_wav(path: Path) -> tuple[list[float], int]:
    with wave.open(str(path), "rb") as handle:
        if handle.getnchannels() != 1 or handle.getsampwidth() != 2:
            raise SystemExit("expected mono 16-bit WAV")
        rate = handle.getframerate()
        raw = handle.readframes(handle.getnframes())
    samples = [int.from_bytes(raw[i : i + 2], "little", signed=True) / 32768 for i in range(0, len(raw), 2)]
    return samples, rate


def envelope(samples: list[float], rate: int) -> list[float]:
    window = max(1, int(rate * 0.04))
    levels = []
    for start in range(0, len(samples), window):
        chunk = samples[start : start + window]
        rms = math.sqrt(sum(value * value for value in chunk) / max(1, len(chunk)))
        levels.append(rms)
    peak = max(levels) or 1.0
    normalized = [min(1.0, value / peak) for value in levels]
    smoothed = []
    state = 0.0
    for value in normalized:
        state = 0.65 * state + 0.35 * value
        smoothed.append(state)
    return smoothed


def frame_at(level: float) -> int:
    if level < 0.04:
        return -1
    return min(4, int(level * 5))


def load(state: str, index: int) -> Image.Image:
    return Image.open(FRAMES / state / f"frame-{index:03d}.png").convert("RGBA")


def sway(image: Image.Image, t: float) -> Image.Image:
    angle = math.sin(2 * math.pi * 0.13 * t) * 1.1
    dx = math.sin(2 * math.pi * 0.21 * t) * 0.7
    dy = math.sin(2 * math.pi * 0.5 * t) * 0.4
    return image.rotate(angle, resample=Image.BICUBIC, translate=(dx, dy), fillcolor=(0, 0, 0, 0))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--audio", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--markers")
    args = parser.parse_args()

    samples, rate = read_wav(Path(args.audio))
    levels = envelope(samples, rate)
    duration = len(samples) / rate
    frames = int(duration * FPS)
    markers = []
    if args.markers:
        markers = json.loads(Path(args.markers).read_text(encoding="utf-8"))
    rng = random.Random(7)
    blink_start = rng.uniform(2.0, 3.5)
    blinks = []
    while blink_start < duration:
        blinks.append(blink_start)
        blink_start += rng.uniform(3.2, 6.0)

    idle = load("idle", 0)
    blink = load("blink", 12)
    mouths = {i: load("talking", frame) for i, frame in enumerate(MOUTH_FRAMES)}
    reactions = {state: load(state, len(list((FRAMES / state).glob("frame-*.png"))) // 2) for state in ("happy", "surprised", "confused", "proud", "sad")}

    OUT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        for index in range(frames):
            t = index / FPS
            level = levels[min(len(levels) - 1, int(t * len(levels) / duration))]
            mouth = frame_at(level)
            image = idle if mouth < 0 else mouths[mouth]
            for start in blinks:
                if start <= t < start + 0.13:
                    image = blink
                    break
            for marker in markers:
                if abs(t - float(marker["t"])) < 0.6 and marker["state"] in reactions:
                    image = reactions[marker["state"]]
                    break
            sway(image, t).save(tmp_path / f"frame-{index:04d}.png")
        import imageio_ffmpeg

        ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            [ffmpeg, "-y", "-hide_banner", "-loglevel", "error", "-framerate", str(FPS), "-i", str(tmp_path / "frame-%04d.png"),
             "-c:v", "prores_ks", "-profile:v", "4444", "-pix_fmt", "yuva444p10le", str(out)],
            check=True,
        )
        print(f"wrote {out} ({frames} frames, {duration:.2f}s, amplitude-driven)")


if __name__ == "__main__":
    main()
