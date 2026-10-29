"""Pipeline background wiring: suppression, fallback and the failure fallback."""

from pathlib import Path
from types import SimpleNamespace

import numpy as np
from PIL import Image

from app.pipeline import background, job as job_module
from app.pipeline.document import Document, _attach_background
from app.pipeline.meta import SamObject
from app.pipeline.types import PageJob


def _page(tmp_path: Path) -> tuple[Path, Image.Image]:
    Image.new("RGB", (120, 90), (255, 255, 255)).save(tmp_path / "source.png")
    composite = Image.new("RGBA", (120, 90), (255, 255, 255, 255))
    return tmp_path, composite


def _sam(width: int, height: int, x: int, y: int) -> SamObject:
    mask_w, mask_h = 20, 20
    return SamObject(
        object_id="1",
        box=(x, y, x + mask_w, y + mask_h, width, height),
        confidence=0.9,
        width=mask_w,
        height=mask_h,
        raster=b"\x01" * (mask_w * mask_h),
    )


def test_sam_zero_objects_suppresses_all_bubbles(tmp_path: Path, monkeypatch) -> None:
    folder, composite = _page(tmp_path)
    monkeypatch.setattr(
        background,
        "sam_segment",
        lambda *_args, **_kwargs: ([], SimpleNamespace(images=1)),
    )
    summary = background.build_assets(
        folder,
        b"x",
        composite,
        [{"id": "t1", "bbox": [10, 10, 50, 40], "type": "dialogue"}],
        120,
        90,
    )
    assert summary["counts"] == {
        "bubbles": 0,
        "sam": 0,
        "box_fallback": 0,
        "fallback_suppressed": True,
    }
    manifest = background.json.loads((folder / "background.json").read_text(encoding="utf-8"))
    assert manifest["bubbles"] == []
    assert manifest["counts"]["fallback_suppressed"] is True


def test_one_sam_object_keeps_box_fallback_for_unmatched_region(tmp_path: Path, monkeypatch) -> None:
    folder, composite = _page(tmp_path)
    monkeypatch.setattr(
        background,
        "sam_segment",
        lambda *_args, **_kwargs: ([_sam(120, 90, 5, 5)], SimpleNamespace(images=1)),
    )
    summary = background.build_assets(
        folder,
        b"x",
        composite,
        [
            {"id": "t1", "bbox": [5, 5, 25, 25], "type": "dialogue"},
            {"id": "t2", "bbox": [70, 50, 110, 80], "type": "dialogue"},
        ],
        120,
        90,
    )
    assert summary["counts"] == {
        "bubbles": 2,
        "sam": 1,
        "box_fallback": 1,
        "fallback_suppressed": False,
    }
    sources = [bubble["source"] for bubble in background.json.loads((folder / "background.json").read_text(encoding="utf-8"))["bubbles"]]
    assert sorted(sources) == ["box_fallback", "sam"]


def test_background_failure_is_recorded_and_does_not_raise(tmp_path: Path, monkeypatch) -> None:
    job = PageJob(id="bg-fail", register="egyptian", width=120, height=90)
    composite = Image.new("RGB", (120, 90), "white")

    def boom(*_args, **_kwargs):
        raise RuntimeError("injected background failure")

    monkeypatch.setattr(job_module, "build_assets", boom)
    job_module._background_stage(job, tmp_path, b"x", composite, [], 120, 90)

    stage = job.stages[-1]
    assert stage.name == "background"
    assert "injected background failure" in stage.detail["error"]
    assert any("background layers unavailable" in warning for warning in job.warnings)


def test_captions_items_and_prices_never_become_bubbles(tmp_path: Path, monkeypatch) -> None:
    folder, composite = _page(tmp_path)
    called = {"sam": 0}

    def fake_sam(*_args, **_kwargs):
        called["sam"] += 1
        return ([_sam(120, 90, 5, 5)], SimpleNamespace(images=1))

    monkeypatch.setattr(background, "sam_segment", fake_sam)
    summary = background.build_assets(
        folder,
        b"x",
        composite,
        [
            {"id": "t1", "bbox": [5, 5, 25, 25], "type": "caption"},
            {"id": "t2", "bbox": [40, 5, 70, 25], "type": "menu_item"},
            {"id": "t3", "bbox": [75, 5, 105, 25], "type": "price"},
        ],
        120,
        90,
    )
    assert called["sam"] == 0  # no dialogue means no SAM call at all
    assert summary["counts"] == {
        "bubbles": 0,
        "sam": 0,
        "box_fallback": 0,
        "fallback_suppressed": False,
    }


def test_caption_near_a_sam_bubble_is_still_skipped(tmp_path: Path, monkeypatch) -> None:
    folder, composite = _page(tmp_path)
    monkeypatch.setattr(
        background,
        "sam_segment",
        lambda *_args, **_kwargs: ([_sam(120, 90, 5, 5)], SimpleNamespace(images=1)),
    )
    summary = background.build_assets(
        folder,
        b"x",
        composite,
        [
            {"id": "t1", "bbox": [5, 5, 25, 25], "type": "caption"},
            {"id": "t2", "bbox": [10, 10, 24, 24], "type": "dialogue"},
        ],
        120,
        90,
    )
    assert summary["counts"]["bubbles"] == 1
    assert summary["counts"]["sam"] == 1
    assert summary["counts"]["box_fallback"] == 0


def test_manifest_attaches_layers(tmp_path: Path) -> None:
    folder, composite = _page(tmp_path)
    background.build_assets(folder, b"x", composite, [], 120, 90)
    manifest = background.json.loads((folder / "background.json").read_text(encoding="utf-8"))
    manifest["bubbles"] = [
        {"id": "bubble-t1", "box": [10, 10, 50, 40], "asset": "bubble-t1.png", "name": "Bubble", "source": "sam"}
    ]
    (folder / "background.json").write_text(background.json.dumps(manifest), encoding="utf-8")
    Image.new("RGBA", (40, 30), (255, 0, 0, 255)).save(folder / "bubble-t1.png")
    document = Document(id="x", width=120, height=90, layers=[])
    _attach_background(folder, document)
    assert [layer.kind for layer in document.layers] == ["scene", "bubble"]
