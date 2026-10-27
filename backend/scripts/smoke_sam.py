"""Probe 2 — SAM 3.1 segmentation: exact wire format, decodability, cost.

SAM streams one special-token line per frame. This probe records the raw line, parses
boxes and mask descriptors, tries every plausible mask decoding, and renders an
overlay so the result can be inspected rather than trusted.
"""

from __future__ import annotations

import base64
import json
import sys
import time
import zlib
from pathlib import Path

from PIL import Image

from _probe import PRICE, data_url, parse_sam_line, receipt, stream_sse, summarize, SAM_MODEL


def try_decode_mask(mask: dict) -> dict:
    """Attempt the known encodings; report what actually decodes to H*W bits."""
    height, width = mask["height"], mask["width"]
    if not height or not width:
        return {"decoded": False, "reason": "missing H,W"}
    payload = mask["payload"].encode("ascii", "replace")
    expected_bits = height * width
    expected_bytes = (expected_bits + 7) // 8
    out = {
        "height": height,
        "width": width,
        "encoding": mask["encoding"],
        "payload_chars": len(mask["payload"]),
        "expected_bytes_1bpp": expected_bytes,
        "attempts": {},
    }

    def unpack(bits: bytes) -> bytes:
        raster = bytearray(expected_bits)
        for i in range(expected_bits):
            raster[i] = (bits[i >> 3] >> (7 - (i & 7))) & 1
        return bytes(raster)

    candidates: dict[str, bytes] = {}
    for name, fn in {
        "a85_adobe": lambda p: base64.a85decode(p, adobe=False),
        "a85_adobe_frame": lambda p: base64.a85decode(b"<~" + p + b"~>", adobe=True),
        "b85_rfc1924": lambda p: base64.b85decode(p),
    }.items():
        try:
            candidates[name] = fn(payload)
        except Exception as exc:  # noqa: BLE001 - probe records, never raises
            out["attempts"][name] = f"error: {type(exc).__name__}: {exc}"

    raster = None
    for name, raw in candidates.items():
        out["attempts"][name] = {"bytes": len(raw), "head": raw[:8].hex()}
        if len(raw) >= expected_bytes:
            raster = unpack(raw[:expected_bytes])
            out["decoded_with"] = name
            break
        try:
            inflated = zlib.decompress(raw)
            out["attempts"][name]["zlib_bytes"] = len(inflated)
            if len(inflated) >= expected_bytes:
                raster = unpack(inflated[:expected_bytes])
                out["decoded_with"] = f"{name}+zlib"
                break
        except zlib.error:
            pass

    if raster is None:
        out["decoded"] = False
        return out

    out["decoded"] = True
    out["foreground_pixels"] = sum(raster)
    out["foreground_ratio"] = round(sum(raster) / expected_bits, 4)
    out["_raster"] = raster
    return out


def render_overlay(image_path: Path, frame: dict, decodes: list[dict], out_path: Path) -> None:
    base = Image.open(image_path).convert("RGBA")
    overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
    tint = Image.new("RGBA", base.size, (229, 72, 77, 110))
    for decode in decodes:
        if not decode.get("decoded"):
            continue
        raster = decode.pop("_raster")
        mask = Image.frombytes("L", (decode["width"], decode["height"]), bytes(255 if b else 0 for b in raster))
        mask = mask.resize(base.size, Image.NEAREST)
        overlay.paste(tint, (0, 0), mask)
    Image.alpha_composite(base, overlay).convert("RGB").save(out_path)


def main() -> None:
    image = Path(sys.argv[1] if len(sys.argv) > 1 else "assets/generated/test-panel.png")
    prompt = sys.argv[2] if len(sys.argv) > 2 else "text"
    if not image.is_file():
        raise SystemExit(f"image not found: {image} (run smoke_image_generate.py first)")

    request = {
        "model": SAM_MODEL,
        "input": [
            {
                "type": "message",
                "role": "user",
                "content": [
                    {"type": "input_text", "text": prompt},
                    {"type": "input_image", "image_url": data_url(image)},
                ],
            }
        ],
        "metadata": {"mask_encoding": "one_bit", "include_confidence": "true"},
    }

    started = time.perf_counter()
    deltas: list[str] = []
    events = 0
    completed = False
    usage: dict = {}
    for event in stream_sse("/responses", request):
        events += 1
        kind = event.get("type")
        if kind == "response.output_text.delta":
            deltas.append(event.get("delta", ""))
        elif kind == "response.completed":
            completed = True
            usage = (event.get("response") or {}).get("usage") or {}
        elif kind == "response.failed":
            usage = event
    latency_ms = int((time.perf_counter() - started) * 1000)

    text = "".join(deltas)
    line = text.strip()
    frame = parse_sam_line(line) if line else {"frame": None, "boxes": [], "masks": [], "raw_len": 0}
    decodes = [try_decode_mask(m) for m in frame["masks"]]

    overlay_path = None
    if any(d.get("decoded") for d in decodes):
        overlay = image.parent / f"{image.stem}-{prompt.replace(' ', '-')}-masks.png"
        render_overlay(image, frame, decodes, overlay)
        overlay_path = str(overlay)

    path = receipt(
        "sam",
        {
            "image": str(image),
            "prompt": prompt,
            "request": {**request, "input": "…image elided…"},
            "latency_ms": latency_ms,
            "sse_events": events,
            "completed": completed,
            "raw_output_text": text,
            "frame": {k: v for k, v in frame.items() if k != "masks"},
            "mask_summaries": [{k: v for k, v in d.items() if k != "_raster"} for d in decodes],
        },
    )

    summarize(
        "sam_segment",
        model=SAM_MODEL,
        result=type("R", (), {"status": 200 if completed else 0, "latency_ms": latency_ms, "body": {"usage": usage}, "headers": {}})(),
        extra={
            "prompt": prompt,
            "image": str(image),
            "sse_events": events,
            "output_chars": len(text),
            "frames": 1 if line else 0,
            "objects": len(frame["boxes"]),
            "boxes": frame["boxes"],
            "masks": [{k: v for k, v in d.items() if k != "_raster"} for d in decodes],
            "overlay_png": overlay_path,
            "cost_usd_estimate": PRICE["sam_per_image"],
            "receipt": str(path),
        },
    )


if __name__ == "__main__":
    main()
