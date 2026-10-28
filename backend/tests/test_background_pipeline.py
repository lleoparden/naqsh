"""Pipeline background wiring: manifest sources and no-bubble pages."""

from pathlib import Path
from types import SimpleNamespace

import numpy as np
from PIL import Image

from app.pipeline import background
from app.pipeline.document import Document, _attach_background


def _page(tmp_path: Path) -> tuple[Path, Image.Image]:
    Image.new("RGB", (120, 90), (255, 255, 255)).save(tmp_path / "source.png")
    composite = Image.new("RGBA", (120, 90), (255, 255, 255, 255))
    return tmp_path, composite


def test_no_candidates_writes_scenery_only(tmp_path: Path, monkeypatch) -> None:
    folder, composite = _page(tmp_path)

    def boom(*_args, **_kwargs):
        raise AssertionError("SAM must not be called when there are no dialogue/caption regions")

    monkeypatch.setattr(background, "sam_segment", boom)
    summary = background.build_assets(
        folder, b"x", composite, [{"id": "t1", "bbox": [10, 10, 60, 30], "type": "menu_item"}], 120, 90
    )
    assert summary["counts"] == {"bubbles": 0, "sam": 0, "box_fallback": 0}
    assert (folder / "scene.png").is_file()
    assert background.json.loads((folder / "background.json").read_text(encoding="utf-8"))["bubbles"] == []


def test_missing_sam_mask_is_recorded_as_box_fallback(tmp_path: Path, monkeypatch) -> None:
    folder, composite = _page(tmp_path)
    monkeypatch.setattr(
        background,
        "sam_segment",
        lambda *_args, **_kwargs: ([], SimpleNamespace(images=1)),
    )
    summary = background.build_assets(
        folder, b"x", composite, [{"id": "t1", "bbox": [10, 10, 50, 40], "type": "dialogue"}], 120, 90
    )
    assert summary["counts"] == {"bubbles": 1, "sam": 0, "box_fallback": 1}
    manifest = background.json.loads((folder / "background.json").read_text(encoding="utf-8"))
    assert manifest["bubbles"][0]["source"] == "box_fallback"
    assert manifest["counts"]["box_fallback"] == 1
    scene = np.asarray(Image.open(folder / "scene.png").convert("RGBA"))
    assert scene[20, 20, 3] == 0  # hole cut for the bubble


def test_manifest_attaches_layers(tmp_path: Path) -> None:
    folder, composite = _page(tmp_path)
    background.build_assets(
        folder, b"x", composite, [], 120, 90
    )
    manifest = background.json.loads((folder / "background.json").read_text(encoding="utf-8"))
    manifest["bubbles"] = [
        {"id": "bubble-t1", "box": [10, 10, 50, 40], "asset": "bubble-t1.png", "name": "Bubble", "source": "sam"}
    ]
    (folder / "background.json").write_text(background.json.dumps(manifest), encoding="utf-8")
    Image.new("RGBA", (40, 30), (255, 0, 0, 255)).save(folder / "bubble-t1.png")
    document = Document(id="x", width=120, height=90, layers=[])
    _attach_background(folder, document)
    assert [layer.kind for layer in document.layers] == ["scene", "bubble"]
