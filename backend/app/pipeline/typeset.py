"""Typesetting stage: fit an Arabic line into the space the original lettering had.

Phase 2 uses arabic-reshaper + bidi with presentation-form fonts (Noto Kufi / Noto
Naskh). Phase 3 replaces this with a HarfBuzz shaper and a style matcher; the
interface (``fit_text`` returning display lines and a size) is designed to survive
that swap.

Fitting measures *ink*, not the em box: a Kufi alef or a final kaf easily extends
past its nominal size, and that is exactly how text gets clipped in a caption bar.
"""

from __future__ import annotations

from pathlib import Path

import arabic_reshaper
from bidi.algorithm import get_display
from PIL import ImageFont

from .types import Layout

REPO_ROOT = Path(__file__).resolve().parents[3]
FONT_DIR = REPO_ROOT / "assets" / "fonts"

FONTS: dict[str, Path] = {
    # Comic lettering reads best in a geometric kufi; naskh is the publishing option.
    "kufi": FONT_DIR / "NotoKufiArabic-Variable.ttf",
    "naskh": FONT_DIR / "NotoNaskhArabic-Variable.ttf",
    "amiri": FONT_DIR / "Amiri-Regular.ttf",
}

DEFAULT_FAMILY = "kufi"
LINE_GAP_RATIO = 0.18


def display_text(text: str) -> str:
    """Reshape and reorder for rendering by a non-shaping rasteriser."""
    return get_display(arabic_reshaper.reshape(text.strip()))


def available_families() -> list[str]:
    return [name for name, path in FONTS.items() if path.is_file()]


def _font(family: str, size: int) -> ImageFont.FreeTypeFont:
    path = FONTS.get(family) or FONTS[DEFAULT_FAMILY]
    if not path.is_file():
        raise FileNotFoundError(f"font missing: {path}")
    return ImageFont.truetype(str(path), max(6, size))


def _wrap(words: list[str], font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    lines: list[str] = []
    current: list[str] = []
    for word in words:
        candidate = " ".join([*current, word])
        width = font.getlength(display_text(candidate))
        if current and width > max_width:
            lines.append(" ".join(current))
            current = [word]
        else:
            current.append(word)
    if current:
        lines.append(" ".join(current))
    return lines


def _measure(lines: list[str], font: ImageFont.FreeTypeFont, size: int) -> tuple[int, int]:
    """Ink width and stacked ink height for display lines."""
    widths: list[int] = []
    heights: list[int] = []
    for line in lines:
        box = font.getbbox(display_text(line))
        widths.append(box[2] - box[0])
        heights.append(box[3] - box[1])
    gap = int(round(size * LINE_GAP_RATIO))
    total_height = sum(heights) + gap * (len(lines) - 1)
    return max(widths, default=0), total_height


def fit_text(
    text: str,
    box_width: int,
    box_height: int,
    *,
    family: str = DEFAULT_FAMILY,
    max_size: int | None = None,
    min_size: int = 10,
    padding: int = 6,
) -> Layout:
    """Largest size at which the whole line fits, wrapping only when it must."""
    width = max(8, int(box_width * 0.94) - 2 * padding)
    # Spark's boxes are a little loose around a caption bar; 0.82 of the box height
    # is the conservative budget that keeps descenders inside the artwork.
    height = max(8, int(box_height * 0.82) - 2 * padding)
    words = [w for w in text.split() if w]
    if not words:
        return Layout(lines=[], size=min_size, line_height=min_size, width=0, height=0)

    upper = min(max_size or height, height, max(12, int(height * 1.1)))
    for size in range(upper, min_size - 1, -1):
        font = _font(family, size)
        lines = _wrap(words, font, width)
        ink_width, ink_height = _measure(lines, font, size)
        if ink_width <= width and ink_height <= height:
            return Layout(
                lines=[display_text(line) for line in lines],
                size=size,
                line_height=int(round(size * (1 + LINE_GAP_RATIO))),
                width=ink_width,
                height=ink_height,
            )

    font = _font(family, min_size)
    lines = _wrap(words, font, width)
    ink_width, ink_height = _measure(lines, font, min_size)
    return Layout(
        lines=[display_text(line) for line in lines],
        size=min_size,
        line_height=int(round(min_size * (1 + LINE_GAP_RATIO))),
        width=ink_width,
        height=ink_height,
        overflow=True,
    )
