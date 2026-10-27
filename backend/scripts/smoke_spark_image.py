"""Probe 1b — Muse Spark with an image: read the page, propose Arabic layers.

This is the shape the product needs: per text region, a source transcription, a
bounding box, a natural Arabic line, and a style call. The probe reports whether the
model returns usable JSON (compliance matters as much as the translation).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from _probe import SPARK_MODEL, data_url, post_json, receipt, response_text, spark_cost, summarize, usage_of

PROMPT = """You are the text engine of an Arabic localization tool for comics and posters.

Look at this image. Find every text region that a localizer would need to replace.
For each one return:
- "id": short stable id (t1, t2, ...)
- "source_text": the exact text you can read
- "bbox_norm": [x0, y0, x1, y1] as fractions of image width/height (0-1)
- "translation_ar": natural Arabic, same meaning and tone, short enough to fit the space
- "style": one of "speech", "caption", "title", "label"
- "font_style": one short phrase describing the original lettering (e.g. "bold rounded uppercase sans")

Return strict JSON only: {"regions": [ ... ]}
If a region is unreadable, keep it and set source_text to "".
"""


def main() -> None:
    image = Path(sys.argv[1] if len(sys.argv) > 1 else "assets/generated/test-panel.png")
    if not image.is_file():
        raise SystemExit(f"image not found: {image} (run smoke_image_generate.py first)")

    payload = {
        "model": SPARK_MODEL,
        "input": [
            {
                "type": "message",
                "role": "user",
                "content": [
                    {"type": "input_text", "text": PROMPT},
                    {"type": "input_image", "image_url": data_url(image)},
                ],
            }
        ],
        "reasoning": {"effort": "minimal"},
        "max_output_tokens": 2400,
    }
    result = post_json("/responses", payload, timeout=180.0)
    text = response_text(result.body)
    parsed = None
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start >= 0 and end > start:
            try:
                parsed = json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                parsed = None

    path = receipt(
        "spark-image",
        {
            "image": str(image),
            "request": payload,
            "http_status": result.status,
            "latency_ms": result.latency_ms,
            "body": result.body,
            "output_text": text,
        },
    )
    usage = usage_of(result.body)
    summarize(
        "spark_image",
        model=SPARK_MODEL,
        result=result,
        extra={
            "image": str(image),
            "json_parsed": parsed is not None,
            "region_count": len(parsed.get("regions", [])) if isinstance(parsed, dict) else None,
            "regions": parsed.get("regions") if isinstance(parsed, dict) else None,
            "output_text": text[:2000],
            "cost_usd_estimate": spark_cost(usage),
            "receipt": str(path),
        },
    )


if __name__ == "__main__":
    main()
