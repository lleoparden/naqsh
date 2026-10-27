"""Muse Spark visual self-check on the rendered page.

After the Arabic is drawn, one vision call looks at 100%-zoom crops and asks per
region whether the text is actually OK in place: overflow, clipping, unreadable, or
a translation that does not match the source. It is the same model that read the
page, now checking the result — and it only ever gets one fix pass.
"""

from __future__ import annotations

import io
from dataclasses import dataclass
from typing import Any

from PIL import Image

from .meta import Usage, spark_json
from .types import Layout, TextRegion

ISSUES = ("overflow", "clipping", "unreadable", "bad_translation", "none")

PROMPT = """These are {count} crops from a localized page at 100% zoom. Each label gives the crop id, the source text it replaced, and the Arabic that was drawn there.

Judge two things, in this order:
1. Meaning: does the Arabic say the same thing as the source (same intent, names and numbers)? If it says something unrelated, or is a transliteration instead of Arabic, the issue is "bad_translation" — even if it fits perfectly.
2. Fit: only for a correct translation, is the Arabic properly inside the balloon/box? Use "overflow" when it runs past the edge or over artwork, "clipping" when letters, ascenders or diacritics are cut off, "unreadable" when it is too small, too faint, or overlapping itself. Otherwise "none".

Be strict about fit but do not invent meaning problems: a faithful Arabic line is "none".
Return strict JSON only:
{{"regions": [{{"id": "t1", "ok": true, "issue": "none", "note": "short reason"}}]}}"""


@dataclass
class Verdict:
    region_id: str
    issue: str
    note: str

    @property
    def ok(self) -> bool:
        return self.issue == "none"


def _crop(image: Image.Image, region: TextRegion, pad: int = 40, max_width: int = 460) -> Image.Image:
    bbox = region.bbox
    piece = image.crop(
        (
            max(0, bbox.x1 - pad),
            max(0, bbox.y1 - pad),
            min(image.width, bbox.x2 + pad),
            min(image.height, bbox.y2 + pad),
        )
    )
    if piece.width > max_width:
        ratio = max_width / piece.width
        piece = piece.resize((max_width, max(32, int(piece.height * ratio))), Image.LANCZOS)
    return piece


def build_montage(image: Image.Image, regions: list[TextRegion]) -> Image.Image:
    from PIL import ImageDraw

    crops = [(region, _crop(image, region)) for region in regions]
    width = max(piece.width for _r, piece in crops)
    label_h = 30
    height = sum(piece.height + label_h + 6 for _r, piece in crops)
    sheet = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(sheet)
    y = 0
    for region, piece in crops:
        label = f"{region.id} | source: {region.source_text[:40]} | arabic: {region.translation_ar[:48]}"
        draw.rectangle([0, y, width, y + label_h], fill=(242, 238, 228))
        draw.text((6, y + 8), label, fill=(20, 17, 15))
        sheet.paste(piece, (0, y + label_h))
        y += piece.height + label_h + 6
    return sheet


def check_render(image: Image.Image, regions: list[TextRegion]) -> tuple[list[Verdict], Usage, str]:
    montage = build_montage(image, regions)
    buffer = io.BytesIO()
    montage.save(buffer, format="PNG")
    prompt = PROMPT.format(count=len(regions))
    payload, usage, raw = spark_json(buffer.getvalue(), prompt, max_output_tokens=1200)
    verdicts: list[Verdict] = []
    for item in payload.get("regions") or []:
        if not isinstance(item, dict):
            continue
        issue = str(item.get("issue") or ("none" if item.get("ok") else "unreadable")).lower()
        if issue not in ISSUES:
            issue = "unreadable"
        verdicts.append(Verdict(region_id=str(item.get("id") or ""), issue=issue, note=str(item.get("note") or "")))
    return verdicts, usage, raw


def apply_fix(
    regions: list[TextRegion],
    layouts: dict[str, Layout],
    verdicts: list[Verdict],
    fit,
) -> list[str]:
    """Shrink layout for fitting issues; leave translation issues to the caller."""
    fixed: list[str] = []
    by_id = {region.id: region for region in regions}
    for verdict in verdicts:
        if verdict.ok or verdict.issue == "bad_translation":
            continue
        region = by_id.get(verdict.region_id)
        layout = layouts.get(verdict.region_id)
        if region is None or layout is None:
            continue
        box = region.container or region.bbox
        smaller = fit(
            region.translation_ar,
            box.width,
            box.height,
            family=region.font_family,
            max_size=max(10, int(layout.size * 0.8)),
        )
        layouts[region.id] = smaller
        region.font_size = smaller.size
        region.lines = smaller.lines
        fixed.append(region.id)
    return fixed


def summarise(verdicts: list[Verdict]) -> dict[str, Any]:
    return {
        "flagged": [v.region_id for v in verdicts if not v.ok],
        "issues": {v.region_id: v.issue for v in verdicts if not v.ok},
        "notes": {v.region_id: v.note for v in verdicts if v.note},
    }
