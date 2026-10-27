"""Probe 3a — Muse Image generation: produce the safe test panel.

The panel is generated for this project (no third-party art), so it is the one image
every other probe runs on. Prompt is fixed so the artifact is reproducible in spirit;
the API exposes no seed, so pixels may differ between runs.
"""

from __future__ import annotations

import base64
import json
from pathlib import Path

from _probe import IMAGE_MODEL, PRICE, post_json, receipt, summarize

OUT = Path(__file__).resolve().parents[2] / "assets" / "generated" / "test-panel.png"

PROMPT = (
    "A clean comic page panel in flat vector style, original artwork: a small bakery "
    "counter at dusk, a young baker in an apron leaning on the counter, warm lamps, "
    "two empty speech bubbles with black outlines, and one rectangular caption box at "
    "the top. Inside the first speech bubble the plain English words 'FRESH BREAD?' in "
    "bold uppercase lettering; inside the second bubble the words 'EVERY MORNING' in "
    "handwritten style; inside the caption box the words 'CHAPTER ONE'. Simple palette "
    "of cream, terracotta and deep teal, thick clean outlines, no gradients, no signature, "
    "portrait orientation, generous white margins."
)


def main() -> None:
    payload = {
        "model": IMAGE_MODEL,
        "prompt": PROMPT,
        "n": 1,
        "size": "1024x1536",
        "output_format": "png",
        "response_format": "b64_json",
    }
    result = post_json("/images/generations", payload, timeout=300.0)

    saved = None
    error = None
    body = result.body if isinstance(result.body, dict) else {}
    data = body.get("data") or []
    if result.status == 200 and data and data[0].get("b64_json"):
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_bytes(base64.b64decode(data[0]["b64_json"]))
        saved = str(OUT)
    else:
        error = body

    path = receipt(
        "image-generate",
        {
            "request": payload,
            "http_status": result.status,
            "latency_ms": result.latency_ms,
            "body_keys": list(body.keys()),
            "usage": body.get("usage"),
            "error": error,
        },
    )
    summarize(
        "image_generate",
        model=IMAGE_MODEL,
        result=result,
        extra={
            "saved_png": saved,
            "size_bytes": OUT.stat().st_size if OUT.is_file() else None,
            "cost_usd_estimate": PRICE["image_per_image"],
            "receipt": str(path),
        },
    )


if __name__ == "__main__":
    main()
