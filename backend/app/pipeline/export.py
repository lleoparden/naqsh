"""Layered SVG / PNG / ZIP export from the editable document.

The SVG is the primary artifact: a viewBox in source pixels, the plate embedded as a
PNG data URL, cover patches, one <text> element per line (RTL, editable), and a
hidden original reference layer. A second, outlined variant converts every glyph to
a path so it looks right on machines without our fonts, at the cost of editability.
The ZIP carries both SVGs, the plate, the exact OFL font files with their licences,
and a README explaining the install.
"""

from __future__ import annotations

import base64
import io
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.ttLib import TTFont
from PIL import Image, ImageDraw

from . import shaping
from .document import Document, Layer, to_numerals
from .types import BBox

FONT_NAMES = {
    "tajawal": ("Tajawal", 400, "Tajawal-Regular.ttf"),
    "tajawal-bold": ("Tajawal", 700, "Tajawal-Bold.ttf"),
    "naskh": ("Noto Naskh Arabic", 400, "NotoNaskhArabic-Variable.ttf"),
    "amiri": ("Amiri", 400, "Amiri-Regular.ttf"),
}
LICENSES = {
    "tajawal": "OFL-Tajawal.txt",
    "naskh": "OFL-NotoNaskhArabic.txt",
    "amiri": "OFL-Amiri.txt",
}


def _font_info(family: str) -> tuple[str, int, str]:
    return FONT_NAMES.get(family, FONT_NAMES["tajawal"])


def _data_url(path: Path) -> str:
    return "data:image/png;base64," + base64.b64encode(path.read_bytes()).decode("ascii")


def visible_layers(document: Document) -> list[Layer]:
    return [layer for layer in sorted(document.layers, key=lambda item: item.z) if layer.visible]


def _text_layers(document: Document) -> list[Layer]:
    return [
        layer
        for layer in visible_layers(document)
        if layer.kind == "text" and layer.action != "skip" and layer.lines
    ]


def render_png(document: Document, folder: Path) -> Image.Image:
    """Server-side render of the document at source resolution (for parity and PNG)."""
    base = Image.open(folder / document.composite).convert("RGBA")
    draw = ImageDraw.Draw(base)
    for layer in visible_layers(document):
        if layer.kind == "cover" and layer.fill:
            draw.rectangle(layer.box, fill=tuple(layer.fill))  # type: ignore[arg-type]
    for layer in _text_layers(document):
        family = layer.font_family
        for line in layer.lines:
            shaped = shaping.shape_line(line.text, family, line.size)
            top = line.baseline + shaped.ink[1]
            shaping.draw_line(
                base,
                shaped,
                family,
                center_x=line.x,
                top=top,
                color=tuple(layer.color),  # type: ignore[arg-type]
            )
    return base.convert("RGB")


def _outline_path(font: TTFont, glyph_set, glyph_name: str) -> tuple[str, int]:
    pen = SVGPathPen(glyph_set)
    glyph_set[glyph_name].draw(pen)
    upem = font["head"].unitsPerEm
    return pen.getCommands(), upem


def _line_paths(line, family: str) -> list[str]:
    """One SVG path per glyph, positioned in page pixels."""
    _name, _weight, file_name = _font_info(family)
    font = TTFont(shaping.FONT_DIR / file_name)
    glyph_set = font.getGlyphSet()
    order = font.getGlyphOrder()
    upem = font["head"].unitsPerEm
    scale = line.size / upem
    shaped = shaping.shape_line(line.text, family, line.size)
    offset_x = line.x - (shaped.ink[0] + shaped.ink_width / 2)
    paths: list[str] = []
    for gid, x, y_offset, _advance in shaped.glyphs:
        if gid <= 0 or gid >= len(order):
            continue
        commands, _ = _outline_path(font, glyph_set, order[gid])
        if not commands:
            continue
        px = offset_x + x
        py = line.baseline - y_offset
        paths.append(
            f'<path transform="translate({px:.2f},{py:.2f}) scale({scale:.6f},{-scale:.6f})" d="{commands}"/>'
        )
    return paths


def build_svg(document: Document, folder: Path, *, outlined: bool = False) -> str:
    parts: list[str] = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        (
            f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'width="{document.width}" height="{document.height}" '
            f'viewBox="0 0 {document.width} {document.height}" '
            f'xmlns:xlink="http://www.w3.org/1999/xlink">'
        ),
        f"<title>Naqsh — {escape(document.id)}</title>",
        '<g id="plate" data-name="Plate">',
        f'<image x="0" y="0" width="{document.width}" height="{document.height}" '
        f'xlink:href="{_data_url(folder / document.composite)}"/>',
        "</g>",
    ]

    covers = [layer for layer in visible_layers(document) if layer.kind == "cover" and layer.fill]
    if covers:
        parts.append('<g id="covers" data-name="Cover patches">')
        for layer in covers:
            x1, y1, x2, y2 = layer.box
            fill = "#%02x%02x%02x" % tuple(layer.fill[:3])
            parts.append(
                f'<rect id="cover-{escape(layer.id)}" x="{x1}" y="{y1}" width="{x2 - x1}" '
                f'height="{y2 - y1}" fill="{fill}"/>'
            )
        parts.append("</g>")

    parts.append('<g id="text-layers" data-name="Text layers">')
    for layer in _text_layers(document):
        name, weight, _file = _font_info(layer.font_family)
        fill = "#%02x%02x%02x" % tuple(layer.color[:3])
        parts.append(
            f'<g id="layer-{escape(layer.id)}" data-name="{escape(layer.id)}" '
            f'data-type="{escape(layer.type)}" data-action="{escape(layer.action)}">'
        )
        if outlined:
            for line in layer.lines:
                for path in _line_paths(line, layer.font_family):
                    parts.append(path.replace("<path", f'<path fill="{fill}"', 1))
        else:
            for line in layer.lines:
                parts.append(
                    f'<text id="text-{escape(layer.id)}-{abs(hash(line.text)) % 10000}" '
                    f'x="{line.x:.1f}" y="{line.baseline:.1f}" '
                    f'font-family="{escape(name)}" font-size="{line.size}" font-weight="{weight}" '
                    f'fill="{fill}" text-anchor="middle" direction="rtl" unicode-bidi="embed" '
                    f'xml:lang="ar">{escape(line.text)}</text>'
                )
        parts.append("</g>")
    parts.append("</g>")
    parts.append('<g id="original-reference" data-name="Original (reference)" style="display:none">')
    parts.append(
        f'<image x="0" y="0" width="{document.width}" height="{document.height}" '
        f'xlink:href="{_data_url(folder / document.source)}"/>'
    )
    parts.append("</g>")
    parts.append("</svg>")
    return "\n".join(parts)


def _readme(document: Document) -> str:
    return (
        "Naqsh export bundle\n"
        "===================\n\n"
        f"Page: {document.id} ({document.width}x{document.height} px)\n"
        f"Register: {document.register} · numerals: {document.numerals}\n\n"
        "Files\n"
        "- export.svg           editable layered SVG (one <text> per line)\n"
        "- export-outlined.svg  same artwork with text converted to paths, always looks right\n"
        "- plate.png            the cleaned background used by the SVG\n"
        "- fonts/               the exact OFL fonts used, with their licence texts\n\n"
        "Fonts\n"
        "Install the fonts in fonts/ before opening export.svg, or the Arabic will fall\n"
        "back to a system font and the line breaks will look wrong. macOS/Windows: open\n"
        "the .ttf files and choose Install. Linux: copy to ~/.local/share/fonts and run\n"
        "fc-cache -f. export-outlined.svg needs no fonts.\n\n"
        "Layers\n"
        "Every layer is a group with an id and a data-name (Plate, Cover patches, Text\n"
        "layers, Original reference). The original reference group is hidden; unhide it\n"
        "in the layers panel to compare.\n\n"
        "Licences\n"
        "Tajawal, Noto Naskh Arabic and Amiri are licensed under the SIL Open Font\n"
        "License 1.1; the full licence text ships beside each font.\n"
    )


def build_bundle(document: Document, folder: Path) -> bytes:
    editable = build_svg(document, folder, outlined=False)
    outlined = build_svg(document, folder, outlined=True)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("export.svg", editable)
        archive.writestr("export-outlined.svg", outlined)
        archive.write(folder / document.composite, "plate.png")
        archive.writestr("README.md", _readme(document))
        for family, file_name in {name: info[2] for name, info in FONT_NAMES.items()}.items():
            path = shaping.FONT_DIR / file_name
            archive.write(path, f"fonts/{file_name}")
            license_name = LICENSES.get(family)
            if license_name and (shaping.FONT_DIR / license_name).is_file():
                archive.write(shaping.FONT_DIR / license_name, f"fonts/{license_name}")
    return buffer.getvalue()


def layout_boxes(document: Document) -> list[dict]:
    """Layer geometry summary, used by tests and the parity check."""
    rows = []
    for layer in document.layers:
        rows.append(
            {
                "id": layer.id,
                "kind": layer.kind,
                "action": layer.action,
                "box": layer.box,
                "visible": layer.visible,
                "lines": [line.to_dict() for line in layer.lines],
            }
        )
    return rows
