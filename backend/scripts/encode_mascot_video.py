"""Encode mascot frame sequences to alpha WebM (VP9) and green-screen MP4, and verify them."""

from __future__ import annotations

import json
from pathlib import Path

import av
from PIL import Image, ImageChops

FRAMES = Path(r"L:\naqsh-review\mascot-assets\frames")
OUT = Path(r"L:\naqsh-review\mascot-assets\video")
STATES = {"idle": (24, 2.0), "thinking": (24, 2.0), "wave": (18, 1.5), "happy": (18, 1.5), "sad": (18, 1.5)}
FPS = 12


def encode_webm(state: str, count: int) -> dict:
    import subprocess

    import imageio_ffmpeg

    path = OUT / f"naqsh-{state}-{STATES[state][1]:g}s-{count}f-alpha.webm"
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    subprocess.run(
        [
            ffmpeg,
            "-y",
            "-framerate",
            str(FPS),
            "-i",
            str(FRAMES / state / "frame-%03d.png"),
            "-c:v",
            "libvpx-vp9",
            "-pix_fmt",
            "yuva420p",
            "-auto-alt-ref",
            "0",
            "-b:v",
            "0",
            "-crf",
            "28",
            "-metadata:s:v:0",
            "alpha_mode=1",
            str(path),
        ],
        check=True,
        capture_output=True,
    )
    return {"file": str(path), "pix_fmt": "yuva420p", "bytes": path.stat().st_size}


def encode_mp4(state: str, count: int) -> dict:
    path = OUT / f"naqsh-{state}-{STATES[state][1]:g}s-{count}f-green-1024.mp4"
    container = av.open(str(path), "w")
    stream = container.add_stream("libx264", rate=FPS)
    stream.width = stream.height = 1024
    stream.pix_fmt = "yuv420p"
    stream.options = {"crf": "20", "preset": "medium"}
    for index in range(count):
        sprite = Image.open(FRAMES / state / f"frame-{index:03d}.png").convert("RGBA").resize((1024, 1024), Image.LANCZOS)
        canvas = Image.new("RGB", (1024, 1024), (0, 255, 0))
        canvas.paste(sprite, (0, 0), sprite)
        frame = av.VideoFrame.from_image(canvas)
        for packet in stream.encode(frame):
            container.mux(packet)
    for packet in stream.encode():
        container.mux(packet)
    container.close()
    return {"file": str(path), "pix_fmt": stream.pix_fmt, "bytes": path.stat().st_size}


def count_frames(path: Path) -> int:
    with av.open(str(path)) as container:
        return sum(1 for _ in container.decode(video=0))


def alpha_min(path: Path) -> int:
    import subprocess
    import tempfile

    import imageio_ffmpeg

    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    with tempfile.TemporaryDirectory() as tmp:
        probe = Path(tmp) / "frame.png"
        subprocess.run(
            [ffmpeg, "-y", "-c:v", "libvpx-vp9", "-i", str(path), "-frames:v", "1", "-pix_fmt", "rgba", str(probe)],
            check=True,
            capture_output=True,
        )
        image = Image.open(probe).convert("RGBA")
        return image.getchannel("A").getextrema()[0]


def seam(state: str) -> dict:
    first = Image.open(FRAMES / state / "frame-000.png").convert("RGBA")
    last = Image.open(FRAMES / state / "seam.png").convert("RGBA")
    diff = ImageChops.difference(first, last)
    bbox = diff.getbbox()
    extrema = diff.getextrema()
    return {"identical": bbox is None, "bbox": bbox, "max_channel_diff": max(value[1] for value in extrema)}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    report = {}
    for state, (count, _seconds) in STATES.items():
        webm = encode_webm(state, count)
        mp4 = encode_mp4(state, count)
        report[state] = {
            "expected_frames": count,
            "webm": webm,
            "webm_decoded_frames": count_frames(Path(webm["file"])),
            "webm_alpha_min": alpha_min(Path(webm["file"])),
            "mp4": mp4,
            "mp4_decoded_frames": count_frames(Path(mp4["file"])),
            "loop": state in ("idle", "thinking"),
            "loop_seam": seam(state),
        }
        print(state, report[state])
    (OUT / "verification.json").write_text(json.dumps(report, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
