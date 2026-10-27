"""Reading stage: Muse Spark finds the lettering, translates it, and names its style.

One vision call returns everything the fitter needs, which is why text, position,
and style are decided together: an Arabic line that ignores the space it has to fit
is a failed translation for this product.
"""

from __future__ import annotations

from typing import Any

from .meta import MetaAPIError, Usage, spark_json
from .types import BBox, TextRegion

REGISTERS = {
    "egyptian": (
        "Egyptian colloquial Arabic (العامية المصرية) — how people actually speak in Cairo. "
        "Use everyday words and contractions a letterer would write; never formal MSA."
    ),
    "msa": (
        "Modern Standard Arabic (الفصحى) — clear, contemporary written Arabic suitable for "
        "publishing. Natural and idiomatic, not archaic or literal."
    ),
}

PROMPT = """You are the text engine of Naqsh, an Arabic localization tool for comics, posters and menus.

Look at this image and find every piece of lettering a localizer must replace (speech bubbles, captions, titles, labels, menu lines, price tags). Ignore the artwork itself.

For each region return:
- "id": short stable id, t1, t2, ...
- "source_text": the exact words you can read, in their original language and case. Empty string if unreadable.
- "bbox_norm": [x0, y0, x1, y1] as fractions of the image width and height (0-1), tight around the lettering block, not the whole bubble or page.
- "translation_ar": the Arabic a professional letterer would set in that space, same meaning and tone. Keep numbers, prices and proper nouns accurate. It must be short enough to fit the same block.
- "style": one of "speech", "caption", "title", "label".
- "font_style": one short phrase about the original lettering (e.g. "bold rounded uppercase sans", "handwritten brush script").
- "color": approximate hex colour of the original lettering, like "#1b4f52".

Translation register: {register_instruction}

Rules:
- translation_ar must contain Arabic script only (digits and punctuation allowed); no Latin letters, no transliteration.
- Never merge two regions into one, never invent lettering that is not there.
- If the page has no lettering, return {{"regions": []}}.

Return strict JSON only, exactly this shape:
{{"regions": [{{"id": "t1", "source_text": "...", "bbox_norm": [0.1, 0.2, 0.5, 0.3], "translation_ar": "...", "style": "speech", "font_style": "...", "color": "#000000"}}]}}
"""


def read_regions(image_png: bytes, width: int, height: int, register: str) -> tuple[list[TextRegion], Usage]:
    if register not in REGISTERS:
        raise ValueError(f"unknown register: {register}")
    prompt = PROMPT.format(register_instruction=REGISTERS[register])
    payload, usage, _raw = spark_json(image_png, prompt, max_output_tokens=3000)

    raw_regions = payload.get("regions")
    if not isinstance(raw_regions, list):
        raise MetaAPIError(200, "model reply had no regions array")

    regions: list[TextRegion] = []
    for index, item in enumerate(raw_regions):
        if not isinstance(item, dict):
            continue
        bbox_values = item.get("bbox_norm")
        if not isinstance(bbox_values, list) or len(bbox_values) != 4:
            continue
        try:
            bbox = BBox.from_norm([float(v) for v in bbox_values], width, height)
        except (TypeError, ValueError):
            continue
        if bbox.width < 8 or bbox.height < 8:
            continue
        translation = str(item.get("translation_ar") or "").strip()
        if not translation:
            continue
        regions.append(
            TextRegion(
                id=str(item.get("id") or f"t{index + 1}"),
                source_text=str(item.get("source_text") or ""),
                translation_ar=translation,
                style=str(item.get("style") or "speech"),
                font_style=str(item.get("font_style") or ""),
                bbox=bbox,
                color=_parse_color(item.get("color")),
            )
        )
    return regions, usage


def _parse_color(value: Any) -> tuple[int, int, int]:
    text = str(value or "").strip().lstrip("#")
    if len(text) == 3:
        text = "".join(c * 2 for c in text)
    if len(text) == 6:
        try:
            return (int(text[0:2], 16), int(text[2:4], 16), int(text[4:6], 16))
        except ValueError:
            pass
    return (20, 17, 15)
