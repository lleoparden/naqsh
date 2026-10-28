"""Export: SVG structure, outlined variant, PNG size, ZIP contents, numerals."""

import io
import json
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

from PIL import Image

from app.pipeline.document import Document, LineBox, Layer, layout_text
from app.pipeline.export import build_bundle, build_svg, render_png


def _document(tmp_path: Path) -> Document:
    (tmp_path / "composite.png").write_bytes(_png((240, 200, 180)))
    (tmp_path / "source.png").write_bytes(_png((20, 60, 80)))
    layer = Layer(
        id="t1",
        kind="text",
        box=[20, 20, 220, 100],
        type="dialogue",
        action="translate",
        source_text="HELLO",
        arabic={"egyptian": "أهلاً", "msa": "مرحباً"},
        font_family="tajawal",
        color=[20, 17, 15],
        z=0,
    )
    layer.font_size, layer.lines = layout_text("أهلاً", layer.box, family="tajawal")
    cover = Layer(id="c1", kind="cover", box=[5, 5, 30, 30], type="decorative", fill=[250, 250, 250])
    return Document(id="test", width=256, height=256, layers=[layer, cover])


def _png(color: tuple[int, int, int]) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (256, 256), color).save(buffer, format="PNG")
    return buffer.getvalue()


def test_svg_has_layers_and_editable_text(tmp_path: Path) -> None:
    doc = _document(tmp_path)
    svg = build_svg(doc, tmp_path)
    root = ET.fromstring(svg)
    ns = {"svg": "http://www.w3.org/2000/svg"}
    texts = root.findall(".//svg:text", ns)
    assert len(texts) == len(doc.layers[0].lines)
    assert texts[0].get("direction") == "rtl"
    ids = {element.get("id") for element in root.iter()}
    assert "plate" in ids and "text-layers" in ids and "covers" in ids
    assert "original-reference" in ids


def test_outlined_variant_replaces_text_with_paths(tmp_path: Path) -> None:
    doc = _document(tmp_path)
    svg = build_svg(doc, tmp_path, outlined=True)
    root = ET.fromstring(svg)
    ns = {"svg": "http://www.w3.org/2000/svg"}
    assert root.findall(".//svg:text", ns) == []
    assert root.findall(".//svg:path", ns)


def test_png_export_is_source_size(tmp_path: Path) -> None:
    doc = _document(tmp_path)
    image = render_png(doc, tmp_path)
    assert image.size == (256, 256)


def test_zip_bundle_contains_svg_fonts_and_readme(tmp_path: Path) -> None:
    doc = _document(tmp_path)
    data = build_bundle(doc, tmp_path)
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        names = set(archive.namelist())
    assert {"export.svg", "export-outlined.svg", "plate.png", "README.md"} <= names
    assert any(name.startswith("fonts/") and name.endswith(".ttf") for name in names)
    assert any("OFL" in name for name in names)


def test_numerals_follow_the_page_switch() -> None:
    _size, lines = layout_text("20", [0, 0, 120, 60], action="keep", numerals="arabic-indic")
    assert lines and lines[0].text == "٢٠"
    _size, arabic = layout_text("كشري 45", [0, 0, 200, 60], action="translate", numerals="arabic-indic")
    assert arabic[0].text == "كشري ٤٥"
    _size, latin = layout_text("كشري 45", [0, 0, 200, 60], action="translate", numerals="latin")
    assert latin[0].text == "كشري 45"
