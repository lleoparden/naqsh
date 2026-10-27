"""HarfBuzz shaping and FreeType rasterising for Arabic.

Pillow's text drawing does not shape: it places Unicode codepoints one by one, so
Arabic comes out as isolated letters unless the font happens to ship presentation
forms. Here the line is shaped with HarfBuzz (joining, ligatures, mark placement),
then each resulting glyph id is rasterised with FreeType and composited at its
shaped position.

Bidi: Western digits and Latin words inside an Arabic line are shaped as separate
left-to-right runs and the runs are placed right-to-left, so `شاي 25` keeps its
digits in the right order.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import freetype
import numpy as np
import uharfbuzz as hb
from PIL import Image

FONT_DIR = Path(__file__).resolve().parents[3] / "assets" / "fonts"

# family -> (file, weight) ; all SIL OFL, licences beside the files (ASSETS.md).
FONTS: dict[str, tuple[str, int]] = {
    "tajawal": ("Tajawal-Regular.ttf", 400),
    "tajawal-bold": ("Tajawal-Bold.ttf", 700),
    "naskh": ("NotoNaskhArabic-Variable.ttf", 400),
    "amiri": ("Amiri-Regular.ttf", 400),
}

RUN_SPLIT = re.compile(r"([0-9]+|[A-Za-z][A-Za-z0-9'’.-]*)")


@dataclass
class ShapedLine:
    text: str
    size: int
    width: int
    # ink box relative to the line origin (baseline y=0): left, top, right, bottom
    ink: tuple[int, int, int, int]
    glyphs: list[tuple[int, float, float, float]] = field(default_factory=list)  # gid, x, y, advance

    @property
    def ink_width(self) -> int:
        return max(0, self.ink[2] - self.ink[0])

    @property
    def ink_height(self) -> int:
        return max(0, self.ink[3] - self.ink[1])


@lru_cache(maxsize=32)
def _face(family: str, size: int) -> freetype.Face:
    file, _weight = FONTS[family]
    face = freetype.Face(str(FONT_DIR / file))
    face.set_pixel_sizes(0, size)
    return face


@lru_cache(maxsize=32)
def _hb_font(family: str, size: int) -> hb.Font:
    file, _weight = FONTS[family]
    font = hb.Font(hb.Face(hb.Blob.from_file_path(str(FONT_DIR / file))))
    font.scale = (size * 64, size * 64)
    return font


def available_families() -> list[str]:
    return [name for name, (file, _w) in FONTS.items() if (FONT_DIR / file).is_file()]


def _shape_run(text: str, family: str, size: int, rtl: bool) -> list[tuple[int, int, int, int]]:
    font = _hb_font(family, size)
    buffer = hb.Buffer()
    buffer.add_str(text)
    buffer.guess_segment_properties()
    buffer.direction = "rtl" if rtl else "ltr"
    if rtl:
        buffer.script = "Arab"
        buffer.language = "ar"
    hb.shape(font, buffer, {})
    return [
        (info.codepoint, pos.x_advance, pos.x_offset, pos.y_offset)
        for info, pos in zip(buffer.glyph_infos, buffer.glyph_positions)
    ]


def _glyph_ink(family: str, size: int, gid: int, x: float, y_offset: float) -> tuple[float, float, float, float]:
    face = _face(family, size)
    face.load_glyph(gid, freetype.FT_LOAD_DEFAULT)
    metrics = face.glyph.metrics
    left = x + metrics.horiBearingX / 64
    top = -(metrics.horiBearingY / 64) - y_offset / 64
    return left, top, left + metrics.width / 64, top + metrics.height / 64


def shape_line(text: str, family: str, size: int) -> ShapedLine:
    """Shape one line, handling Arabic RTL and embedded LTR runs."""
    runs = [part for part in RUN_SPLIT.split(text) if part]
    shaped_runs = []
    for run in runs:
        is_ltr = bool(re.fullmatch(r"[0-9]+|[A-Za-z][A-Za-z0-9'’.-]*", run))
        shaped_runs.append((run, _shape_run(run, family, size, rtl=not is_ltr), is_ltr))

    widths = [sum(g[1] for g in glyphs) / 64 for _t, glyphs, _l in shaped_runs]
    total = sum(widths)
    glyphs_out: list[tuple[int, float, float, float]] = []
    pen_right = total  # paragraph is RTL: place runs from the right edge leftwards
    ink = [float("inf"), float("inf"), float("-inf"), float("-inf")]
    for (_text, run_glyphs, _is_ltr), width in zip(shaped_runs, widths):
        start = pen_right - width
        pen = start
        for gid, advance, x_offset, y_offset in run_glyphs:
            if gid == 0:
                pen += advance / 64
                continue
            x = pen + x_offset / 64
            glyphs_out.append((gid, x, y_offset / 64, advance / 64))
            left, top, right, bottom = _glyph_ink(family, size, gid, x, y_offset)
            if right > left and bottom > top:
                ink[0] = min(ink[0], left)
                ink[1] = min(ink[1], top)
                ink[2] = max(ink[2], right)
                ink[3] = max(ink[3], bottom)
            pen += advance / 64
        # The next (logical later) run sits to the LEFT of this one.
        pen_right = start

    if ink[0] == float("inf"):
        ink = [0.0, 0.0, 0.0, float(size) * 0.7]
    return ShapedLine(
        text=text,
        size=size,
        width=int(round(total)),
        ink=(int(round(ink[0])), int(round(ink[1])), int(round(ink[2])), int(round(ink[3]))),
        glyphs=glyphs_out,
    )


def measure(text: str, family: str, size: int) -> tuple[int, int]:
    line = shape_line(text, family, size)
    return line.ink_width, line.ink_height


def draw_line(
    canvas: Image.Image,
    line: ShapedLine,
    family: str,
    *,
    center_x: float,
    top: float,
    color: tuple[int, int, int],
) -> None:
    """Draw one shaped line centred on ``center_x`` with its ink top at ``top``."""
    face = _face(family, line.size)
    offset_x = center_x - (line.ink[0] + line.ink_width / 2)
    baseline_y = top - line.ink[1]
    layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    for gid, x, y_offset, _advance in line.glyphs:
        face.load_glyph(gid, freetype.FT_LOAD_RENDER | freetype.FT_LOAD_TARGET_NORMAL)
        bitmap = face.glyph.bitmap
        if not bitmap.width or not bitmap.rows:
            continue
        data = np.array(bitmap.buffer, dtype=np.uint8).reshape(bitmap.rows, bitmap.pitch)[:, : bitmap.width]
        glyph = Image.fromarray(data, mode="L")
        px = int(round(offset_x + x + face.glyph.bitmap_left))
        py = int(round(baseline_y - face.glyph.bitmap_top - y_offset))
        layer.paste(Image.new("RGBA", glyph.size, (*color, 255)), (px, py), glyph)
    canvas.alpha_composite(layer)


def is_rtl_line(text: str) -> bool:
    return bool(re.search(r"[\u0600-\u06FF]", text))
