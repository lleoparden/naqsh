"""Post-read dedupe: one region per piece of lettering.

Spark sometimes returns the same line twice, or returns a menu item and its price as
two overlapping regions. A duplicate (same text, boxes overlapping) is dropped. An
item + price pair is merged only when the price box sits inside the item's box, which
means they are the same line; otherwise the price stays its own region so the policy
can keep its numerals.
"""

from __future__ import annotations

import re

from .types import BBox, TextRegion

NUMERIC = re.compile(r"^\s*[\d٠-٩][\d\s.,/+-]*$")


def iou(a: BBox, b: BBox) -> float:
    x1, y1 = max(a.x1, b.x1), max(a.y1, b.y1)
    x2, y2 = min(a.x2, b.x2), min(a.y2, b.y2)
    if x2 <= x1 or y2 <= y1:
        return 0.0
    inter = (x2 - x1) * (y2 - y1)
    union = a.width * a.height + b.width * b.height - inter
    return inter / union if union else 0.0


def _contains(outer: BBox, inner: BBox) -> bool:
    return outer.x1 <= inner.x1 and outer.y1 <= inner.y1 and outer.x2 >= inner.x2 and outer.y2 >= inner.y2


def _normalise(text: str) -> str:
    return " ".join(text.casefold().split())


def dedupe_regions(regions: list[TextRegion], *, threshold: float = 0.5) -> list[TextRegion]:
    """Drop exact duplicates; fold a price into its line only when it is inside it."""
    kept: list[TextRegion] = []
    dropped = 0
    for region in regions:
        duplicate = next(
            (
                other
                for other in kept
                if _normalise(other.source_text) == _normalise(region.source_text)
                and iou(other.bbox, region.bbox) > threshold
            ),
            None,
        )
        if duplicate is not None:
            dropped += 1
            continue
        # Price region inside an item region that already ends with that number: same
        # line, so the item region owns the pixels.
        if NUMERIC.match(region.source_text or ""):
            host = next(
                (
                    other
                    for other in kept
                    if not other.type == "price"
                    and _contains(other.bbox, region.bbox)
                    and region.source_text.strip() in other.source_text
                ),
                None,
            )
            if host is not None:
                dropped += 1
                continue
        kept.append(region)
    if dropped:
        kept.sort(key=lambda r: (r.bbox.y1, r.bbox.x1))
    return kept
