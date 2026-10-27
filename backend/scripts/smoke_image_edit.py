"""Probe 3b — Muse Image edit: can it remove lettering and repaint the plate?

This decides the pipeline's plan A. There is no mask parameter on the images
endpoints (a multipart ``mask`` field is rejected with 400 ``unsupported_parameter``),
so the question is: given an instruction to erase specific text, how well does the
model preserve the rest of the artwork? The probe saves the edited image so the answer
is judged by looking at it, and records the request shape that worked.
"""

from __future__ import annotations

import base64
import sys
from pathlib import Path

from _probe import IMAGE_MODEL, PRICE, data_url, post_json, receipt, summarize

PROMPT = (
    "Remove all lettering from this comic page: erase the text inside both speech "
    "bubbles and the caption box, and repaint those areas with a clean, empty flat fill "
    "that matches the surrounding artwork. Keep everything else identical — same "
    "characters, same poses, same line art, same colours, same framing. Do not add new "
    "text, objects, logos, or signatures. The bubbles must stay empty and readable as "
    "bubbles."
)


def main() -> None:
    source = Path(sys.argv[1] if len(sys.argv) > 1 else "assets/generated/test-panel.png")
    if not source.is_file():
        raise SystemExit(f"image not found: {source} (run smoke_image_generate.py first)")

    out = source.with_name(f"{source.stem}-cleaned{source.suffix}")
    payload = {
        "model": IMAGE_MODEL,
        "prompt": PROMPT,
        "images": [{"image_url": data_url(source)}],
        "n": 1,
        "output_format": "png",
        "response_format": "b64_json",
    }
    result = post_json("/images/edits", payload, timeout=300.0)

    body = result.body if isinstance(result.body, dict) else {}
    data = body.get("data") or []
    saved = None
    if result.status == 200 and data and data[0].get("b64_json"):
        out.write_bytes(base64.b64decode(data[0]["b64_json"]))
        saved = str(out)

    path = receipt(
        "image-edit",
        {
            "source": str(source),
            "request": {**payload, "images": ["…data url elided…"]},
            "http_status": result.status,
            "latency_ms": result.latency_ms,
            "body_keys": list(body.keys()),
            "error": None if saved else body,
        },
    )
    summarize(
        "image_edit",
        model=IMAGE_MODEL,
        result=result,
        extra={
            "source": str(source),
            "saved_png": saved,
            "size_bytes": out.stat().st_size if out.is_file() else None,
            "cost_usd_estimate": PRICE["image_per_image"],
            "receipt": str(path),
        },
    )


if __name__ == "__main__":
    main()
