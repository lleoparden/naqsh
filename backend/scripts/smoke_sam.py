"""Probe 2 — SAM 3.1 segmentation: exact wire format, decodability, cost.

SAM streams one special-token line per frame. This probe records the raw line and the
raw SSE events, parses boxes and mask descriptors, decodes the masks with Meta's own
``meta-sam-parser`` (the payload is a compressed encoding, not raw bits — a hand
decoder cannot read it), and renders an overlay so the result can be inspected.
"""

from __future__ import annotations

import asyncio
import json
import sys
import time
from pathlib import Path

from PIL import Image

from _probe import PRICE, data_url, parse_sam_line, receipt, stream_sse, summarize, SAM_MODEL


def decode_with_parser(events: list[dict]) -> dict:
    """Decode masks through meta-sam-parser; returns rasters keyed by object id."""
    try:
        from meta_sam_parser import decode_mask_to_raster, image_segmentation_format, parse_responses_stream
    except ImportError:
        return {"available": False, "error": "meta-sam-parser is not installed"}

    async def run() -> object:
        async def gen():
            for event in events:
                yield event

        parsed = parse_responses_stream(gen(), image_segmentation_format())
        return await parsed.final_result()

    try:
        result = asyncio.run(run())
    except Exception as exc:  # noqa: BLE001 - the probe records failures
        return {"available": True, "error": f"{type(exc).__name__}: {exc}"}

    rasters = []
    for record in result.records:
        if getattr(record, "kind", None) != "mask":
            continue
        raster = decode_mask_to_raster(record.mask)
        foreground = sum(raster)
        rasters.append(
            {
                "object_id": record.object_id,
                "height": record.mask.height,
                "width": record.mask.width,
                "encoding": record.mask.encoding,
                "raster_bytes": len(raster),
                "foreground_pixels": foreground,
                "foreground_ratio": round(foreground / len(raster), 4) if raster else 0.0,
                "confidence": record.confidence,
                "_raster": raster,
            }
        )
    diagnostics = [str(d) for d in list(result.diagnostics)[:5]]
    return {
        "available": True,
        "outcome": str(result.outcome),
        "diagnostics": diagnostics,
        "masks": rasters,
    }


def render_overlay(image_path: Path, boxes: list[dict], masks: list[dict], out_path: Path) -> None:
    """Tint each decoded mask over the source image.

    The mask raster is not the whole frame: its height/width match the object's box
    (within a pixel or two), so the mask is pasted at the box position and scaled to
    the box size. Pairing is by order, which matches the records on a single still.
    """
    base = Image.open(image_path).convert("RGBA")
    tint = Image.new("RGBA", base.size, (214, 61, 67, 120))
    overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
    for index, mask in enumerate(masks):
        raster = mask.get("_raster")
        if raster is None or index >= len(boxes):
            continue
        box = boxes[index]
        x1, y1 = int(box["x1"]), int(box["y1"])
        x2, y2 = int(box["x2"]), int(box["y2"])
        binary = Image.frombytes(
            "L",
            (mask["width"], mask["height"]),
            bytes(255 if value else 0 for value in raster),
        ).resize((max(1, x2 - x1), max(1, y2 - y1)), Image.NEAREST)
        overlay.paste(tint.crop((x1, y1, x2, y2)), (x1, y1), binary)
    Image.alpha_composite(base, overlay).convert("RGB").save(out_path)


def main() -> None:
    image = Path(sys.argv[1] if len(sys.argv) > 1 else "assets/generated/test-panel.png")
    prompt = sys.argv[2] if len(sys.argv) > 2 else "speech bubble"
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
    events: list[dict] = []
    deltas: list[str] = []
    completed = False
    usage: dict = {}
    for event in stream_sse("/responses", request):
        events.append(event)
        kind = event.get("type")
        if kind == "response.output_text.delta":
            deltas.append(event.get("delta", ""))
        elif kind == "response.completed":
            completed = True
            usage = (event.get("response") or {}).get("usage") or {}
    latency_ms = int((time.perf_counter() - started) * 1000)

    text = "".join(deltas)
    frame = parse_sam_line(text.strip()) if text.strip() else {"frame": None, "boxes": [], "masks": [], "raw_len": 0}
    decoded = decode_with_parser(events)
    masks = decoded.get("masks", []) if decoded.get("available") else []

    overlay_path = None
    if masks and frame["boxes"]:
        import re

        slug = re.sub(r"[^a-z0-9]+", "-", prompt.lower())[:40].strip("-") or "prompt"
        overlay = image.with_name(f"{image.stem}-{slug}-masks.png")
        render_overlay(image, frame["boxes"], masks, overlay)
        overlay_path = str(overlay)

    path = receipt(
        "sam",
        {
            "image": str(image),
            "prompt": prompt,
            "request": {**request, "input": "…image elided…"},
            "latency_ms": latency_ms,
            "sse_event_count": len(events),
            "completed": completed,
            "raw_output_text": text,
            "frame": {k: v for k, v in frame.items() if k != "masks"},
            "mask_descriptors": [{k: v for k, v in m.items() if k != "_raster"} for m in frame["masks"]],
            "decoded": {k: v for k, v in decoded.items() if k != "masks"},
            "masks": [{k: v for k, v in m.items() if k != "_raster"} for m in masks],
        },
    )

    summarize(
        "sam_segment",
        model=SAM_MODEL,
        result=type(
            "R",
            (),
            {"status": 200 if completed else 0, "latency_ms": latency_ms, "body": {"usage": usage}, "headers": {}},
        )(),
        extra={
            "prompt": prompt,
            "image": str(image),
            "sse_events": len(events),
            "output_chars": len(text),
            "objects": len(frame["boxes"]),
            "boxes": frame["boxes"],
            "parser": {k: v for k, v in decoded.items() if k != "masks"},
            "masks": [{k: v for k, v in m.items() if k != "_raster"} for m in masks],
            "overlay_png": overlay_path,
            "cost_usd_estimate": PRICE["sam_per_image"],
            "receipt": str(path),
        },
    )


if __name__ == "__main__":
    main()
