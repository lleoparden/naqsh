"""The presenter maps a generated sine WAV's loudness to mouth shapes."""

from __future__ import annotations

import math
import sys
import wave
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.mascot_presenter import envelope, frame_at, read_wav


def make_wav(path: Path, seconds: float = 2.0, rate: int = 16000) -> None:
    samples = []
    for index in range(int(seconds * rate)):
        t = index / rate
        amplitude = 0.6 if int(t * 4) % 2 == 0 else 0.05
        samples.append(int(32767 * amplitude * math.sin(2 * math.pi * 220 * t)))
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(rate)
        handle.writeframes(b"".join(value.to_bytes(2, "little", signed=True) for value in samples))


def test_envelope_and_mouth_choice(tmp_path: Path) -> None:
    wav = tmp_path / "sine.wav"
    make_wav(wav)
    samples, rate = read_wav(wav)
    levels = envelope(samples, rate)
    assert len(samples) == 2 * rate
    assert max(levels) > 0.5
    assert min(levels) < 0.2
    loud = frame_at(0.9)
    quiet = frame_at(0.02)
    assert loud >= 3
    assert quiet == -1
