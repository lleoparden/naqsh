"""Detect printed dot leaders in a menu line so they can be repainted away.

Spark's reading box covers a menu line like `KOSHARY ........ 45`, but the dots are
punctuation and the residual checker ignores them, so they survived localization.
Here they are found as small, round, evenly spaced ink blobs in the line's band. The
bbox is then added to the repaint coverage, which replaces the dots with the clean
plate (and the flat-fill / ink-inpaint path if the plate still shows them).
"""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np
from PIL import Image, ImageFilter

from .types import BBox

MIN_DOTS = 5
MAX_DOT_PX = 80
MAX_DOT_SIDE = 10
MIN_DOT_SIDE = 2


@dataclass
class LeaderRun:
    bbox: BBox
    dots: int
    spacing: float


def find_leaders(source: Image.Image, reading_box: BBox, mask: Image.Image) -> LeaderRun | None:
    """Return the dot-leader run near a region, or None.

    Leaders are printed in the same ink as the words, so no colour filter is applied:
    size, aspect and even spacing identify them. Tall components (letters) are
    excluded, which keeps a text row from being mistaken for a dot row.
    """
    canvas = np.asarray(source.convert("RGB"), dtype=np.int16)

    x1, y1 = max(0, reading_box.x1), max(0, reading_box.y1)
    x2, y2 = min(source.width, reading_box.x2), min(source.height, reading_box.y2)
    region = canvas[y1:y2, x1:x2]
    if region.size == 0:
        return None
    # The paper is the bright majority of the line; using the mask interior instead is
    # unreliable because a leader line's SAM mask can be a thin strip.
    luminance = region @ np.array([0.299, 0.587, 0.114])
    paper = region[luminance >= np.percentile(luminance, 60)]
    fill = np.median(paper, axis=0)

    height = reading_box.height
    band_top = max(0, reading_box.y1 - int(height * 0.35))
    band_bottom = min(source.height, reading_box.y2 + int(height * 0.35))
    band_left = max(0, reading_box.x1 - 10)
    band_right = min(source.width, reading_box.x2 + int(reading_box.width * 0.35))
    if band_bottom - band_top < 5 or band_right - band_left < 5:
        return None

    crop = canvas[band_top:band_bottom, band_left:band_right]
    ink = (np.abs(crop - fill).max(axis=2) > 35).astype(np.uint8)
    if ink.sum() < 9:
        return None

    count, _labels, stats, centroids = cv2.connectedComponentsWithStats(ink, connectivity=8)
    dots: list[tuple[float, float, int, int, int, int]] = []
    for label in range(1, count):
        x, y, w, h, area = (int(v) for v in stats[label][:5])
        if area > MAX_DOT_PX or w > MAX_DOT_SIDE or h > MAX_DOT_SIDE:
            continue
        if w < MIN_DOT_SIDE or h < MIN_DOT_SIDE:
            continue
        if not (0.5 <= w / h <= 2.0):
            continue
        dots.append((centroids[label][0], centroids[label][1], x, y, w, h))
    if len(dots) < MIN_DOTS:
        return None

    # Candidates include letter fragments; dots are the ones that line up on one row
    # with even spacing, so group by row and keep the best run.
    rows: dict[int, list[tuple[float, float, int, int, int, int]]] = {}
    for dot in dots:
        rows.setdefault(int(round(dot[1] / 4.0)), []).append(dot)

    best: tuple[float, list[tuple[float, float, int, int, int, int]]] | None = None
    for group in rows.values():
        if len(group) < MIN_DOTS:
            continue
        group.sort(key=lambda item: item[0])
        xs = [item[0] for item in group]
        gaps = np.diff(xs)
        if len(gaps) == 0 or gaps.mean() <= 0:
            continue
        median_gap = float(np.median(gaps))
        if median_gap < 3:
            continue
        if any(not (0.5 * median_gap <= gap <= 1.6 * median_gap) for gap in gaps):
            continue
        if float(gaps.std() / gaps.mean()) > 0.35:
            continue
        if xs[-1] - xs[0] < 3 * median_gap:
            continue
        if best is None or len(group) > len(best[1]):
            best = (median_gap, group)
    if best is None:
        return None
    median_gap, dots = best
    gaps = np.diff([item[0] for item in dots])
    # Dots must sit on one line, not scatter across two text rows.
    ys = [item[1] for item in dots]
    if float(np.std(ys)) > max(3.0, height * 0.25):
        return None

    x1 = min(item[2] for item in dots) + band_left
    y1 = min(item[3] for item in dots) + band_top
    x2 = max(item[2] + item[4] for item in dots) + band_left
    y2 = max(item[3] + item[5] for item in dots) + band_top
    return LeaderRun(
        bbox=BBox(max(0, x1 - 4), max(0, y1 - 4), min(source.width, x2 + 4), min(source.height, y2 + 4)),
        dots=len(dots),
        spacing=round(float(gaps.mean()), 1),
    )
