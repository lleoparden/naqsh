"""Scene/bubble export: groups exist, hidden bubbles are omitted, PNG composites them."""

from pathlib import Path

from PIL import Image

from app.pipeline.document import Document, Layer
from app.pipeline.export import build_svg, render_png


def _document(tmp_path: Path) -> Document:
    Image.new("RGBA", (120, 80), (0, 0, 0, 0)).save(tmp_path / "scene.png")
    Image.new("RGBA", (40, 30), (255, 0, 0, 255)).save(tmp_path / "bubble-t1.png")
    Image.new("RGB", (120, 80), (255, 255, 255)).save(tmp_path / "composite.png")
    Image.new("RGB", (120, 80), (255, 255, 255)).save(tmp_path / "source.png")
    return Document(
        id="bg",
        width=120,
        height=80,
        layers=[
            Layer(id="scene", kind="scene", box=[0, 0, 120, 80], type="background", asset="scene.png", z=-1000),
            Layer(id="bubble-t1", kind="bubble", box=[10, 10, 50, 40], type="bubble", asset="bubble-t1.png", z=-500),
        ],
    )


def test_svg_groups_scenery_and_bubbles(tmp_path: Path) -> None:
    document = _document(tmp_path)
    svg = build_svg(document, tmp_path)
    assert 'data-name="Scenery"' in svg and "data:image/png;base64," in svg
    assert 'id="bubbles"' in svg and 'id="bubble-t1"' in svg


def test_hidden_bubble_is_omitted_and_png_keeps_hole(tmp_path: Path) -> None:
    document = _document(tmp_path)
    document.layers[1].visible = False
    svg = build_svg(document, tmp_path)
    assert 'id="bubbles"' not in svg

    visible = _document(tmp_path)
    png = render_png(visible, tmp_path).convert("RGB")
    assert png.getpixel((20, 20)) == (255, 0, 0)
    assert png.getpixel((100, 70)) == (255, 255, 255)  # transparent scene over white
