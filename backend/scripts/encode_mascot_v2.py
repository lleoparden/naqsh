"""Encode v2 mascot clips to ProRes 4444, alpha WebM and green MP4, with decode checks."""

from __future__ import annotations

import json
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import imageio_ffmpeg
from PIL import Image

ROOT = Path(r"L:\naqsh-review\mascot-assets\v2")
FRAMES = ROOT / "frames"
OUT = ROOT / "video"
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
LOOPS = ["idle", "talking", "thinking", "laughing", "sleepy", "working"]
STATES = LOOPS + ["blink", "curious", "surprised", "confused", "happy", "excited", "proud", "sad", "wave-hello", "wave-goodbye"]
TRANSITIONS = sorted(p.name for p in (FRAMES / "transitions").iterdir() if p.is_dir())


def run(args: list[str]) -> None:
    result = subprocess.run([FFMPEG, "-y", "-hide_banner", "-loglevel", "error", *args], capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(result.stderr[-800:])


def encode(src: Path, name: str, fps: int, size: int, kind: str) -> dict:
    OUT.mkdir(parents=True, exist_ok=True)
    if kind == "prores":
        path = OUT / f"{name}-{size}-{fps}fps-prores4444.mov"
        run(["-framerate", str(fps), "-i", str(src / "frame-%03d.png"), "-c:v", "prores_ks", "-profile:v", "4444", "-pix_fmt", "yuva444p10le", str(path)])
        probe = f"ffprobe not used"
        alpha = alpha_min(path, "prores")
    elif kind == "webm":
        path = OUT / f"{name}-{size}-{fps}fps-alpha.webm"
        run(["-framerate", str(fps), "-i", str(src / "frame-%03d.png"), "-c:v", "libvpx-vp9", "-pix_fmt", "yuva420p", "-auto-alt-ref", "0", "-b:v", "0", "-crf", "28", "-metadata:s:v:0", "alpha_mode=1", str(path)])
        probe = f"ffprobe not used"
        alpha = alpha_min(path, "vp9")
    else:
        path = OUT / f"{name}-{size}-{fps}fps-green.mp4"
        run(["-f", "lavfi", "-i", f"color=c=0x00FF00:s={size}x{size}:r={fps}", "-framerate", str(fps), "-i", str(src / "frame-%03d.png"), "-filter_complex", "[0:v][1:v]overlay=shortest=1", "-c:v", "libx264", "-crf", "20", "-pix_fmt", "yuv420p", str(path)])
        probe = f"ffprobe not used"
        alpha = -1
    return {"file": str(path), "kind": kind, "bytes": path.stat().st_size, "alpha_min": alpha}


def alpha_min(path: Path, decoder: str) -> int:
    with tempfile.TemporaryDirectory() as tmp:
        png = Path(tmp) / "f.png"
        args = ["-c:v", "prores" if decoder == "prores" else "libvpx-vp9", "-i", str(path), "-frames:v", "1", "-pix_fmt", "rgba", str(png)]
        run(args)
        return Image.open(png).convert("RGBA").getchannel("A").getextrema()[0]


def frame_count(path: Path) -> int:
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "f%04d.png"
        run(["-i", str(path), str(out)])
        return len(list(Path(tmp).glob("f*.png")))


def main() -> None:
    jobs = []
    for state in STATES:
        src = FRAMES / "24fps" / state
        for kind in ("prores", "webm", "green"):
            jobs.append((src, f"{state}-24fps", 24, 768, kind))
    for state in STATES:
        jobs.append((FRAMES / "12fps" / state, f"{state}-12fps", 12, 768, "webm"))
    for name in TRANSITIONS:
        jobs.append((FRAMES / "transitions" / name, name, 24, 768, "webm"))
    for state in ("idle", "talking", "happy", "excited"):
        src = FRAMES / "1080" / state
        for kind in ("prores", "webm", "green"):
            jobs.append((src, f"hero-{state}-24fps", 24, 1080, kind))

    results = []
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = [pool.submit(encode, *job) for job in jobs]
        for future in futures:
            results.append(future.result())
    for item in results:
        item["decoded_frames"] = frame_count(Path(item["file"]))
    (OUT / "verification.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"{len(results)} encodes verified")


if __name__ == "__main__":
    main()
