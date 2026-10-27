"""Typesetting: fit a shaped Arabic line into the space the original lettering had.

Fitting uses HarfBuzz-shaped ink extents (not advance widths), so diacritics above
and descenders below are inside the measurement. Lines are balanced when there are
two of them: the break point with the smallest widest-line wins.
"""

from __future__ import annotations

from .shaping import FONTS, available_families, measure, shape_line
from .types import Layout

DEFAULT_FAMILY = "tajawal"
LINE_GAP_RATIO = 0.20


def family_for(font_style: str, style: str = "") -> str:
    """Map Spark's style words to one of the bundled OFL families."""
    text = f"{font_style} {style}".lower()
    if any(word in text for word in ("naskh", "serif", "calligraph", "print", "engraved")):
        return "naskh"
    if "amiri" in text:
        return "amiri"
    if any(word in text for word in ("bold", "title", "display", "heavy", "chalk")):
        return "tajawal-bold"
    return "tajawal"


def _wrap(words: list[str], family: str, size: int, max_width: int) -> list[str]:
    lines: list[str] = []
    current: list[str] = []
    for word in words:
        candidate = " ".join([*current, word])
        width, _height = measure(candidate, family, size)
        if current and width > max_width:
            lines.append(" ".join(current))
            current = [word]
        else:
            current.append(word)
    if current:
        lines.append(" ".join(current))
    return lines


def _block_height(lines: list[str], family: str, size: int) -> int:
    gap = int(round(size * LINE_GAP_RATIO))
    heights = [measure(line, family, size)[1] for line in lines]
    return sum(heights) + gap * max(0, len(lines) - 1)


def _widest(lines: list[str], family: str, size: int) -> int:
    return max((measure(line, family, size)[0] for line in lines), default=0)


def _balanced(words: list[str], family: str, size: int, max_width: int) -> list[str]:
    """For two lines, pick the split with the smallest widest line."""
    if len(words) < 2:
        return [" ".join(words)]
    best: tuple[int, list[str]] | None = None
    for split in range(1, len(words)):
        candidate = [" ".join(words[:split]), " ".join(words[split:])]
        if _widest(candidate, family, size) > max_width:
            continue
        widest = _widest(candidate, family, size)
        if best is None or widest < best[0]:
            best = (widest, candidate)
    return best[1] if best else _wrap(words, family, size, max_width)


def fit_text(
    text: str,
    box_width: int,
    box_height: int,
    *,
    family: str = DEFAULT_FAMILY,
    max_size: int | None = None,
    min_size: int = 10,
    padding: int | None = None,
) -> Layout:
    # Thin caption lines need proportionally less padding than a big bubble.
    if padding is None:
        padding = max(2, min(6, int(min(box_width, box_height) * 0.04)))
    width = max(8, int(box_width * 0.96) - 2 * padding)
    height = max(8, int(box_height * 0.95) - 2 * padding)
    words = [word for word in text.split() if word]
    if not words:
        return Layout(lines=[], size=min_size, line_height=min_size, width=0, height=0)

    upper = min(max_size or height, height, 220)
    for size in range(upper, min_size - 1, -1):
        lines = _wrap(words, family, size, width)
        if _widest(lines, family, size) > width:
            continue
        if _block_height(lines, family, size) > height:
            continue
        if len(lines) == 2:
            lines = _balanced(words, family, size, width)
        widest = _widest(lines, family, size)
        block = _block_height(lines, family, size)
        return Layout(
            lines=lines,
            size=size,
            line_height=int(round(size * (1 + LINE_GAP_RATIO))),
            width=widest,
            height=block,
        )

    lines = _wrap(words, family, min_size, width)
    return Layout(
        lines=lines,
        size=min_size,
        line_height=int(round(min_size * (1 + LINE_GAP_RATIO))),
        width=_widest(lines, family, min_size),
        height=_block_height(lines, family, min_size),
        overflow=True,
    )


def shaped_lines(lines: list[str], family: str, size: int) -> list:
    return [shape_line(line, family, size) for line in lines]


__all__ = [
    "DEFAULT_FAMILY",
    "FONTS",
    "available_families",
    "family_for",
    "fit_text",
    "shape_line",
    "shaped_lines",
]
