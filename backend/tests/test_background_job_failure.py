"""Regression for the BBox conversion and a full-job injected background failure."""

from pathlib import Path
from types import SimpleNamespace

import io

from PIL import Image

from app.pipeline import job as job_module
from app.pipeline.types import BBox, TextRegion


def _region() -> TextRegion:
    return TextRegion(
        id="t1",
        source_text="HELLO",
        translation_ar="مرحبا",
        style="hand-lettered",
        font_style="comic",
        bbox=BBox(10, 20, 110, 60),
        type="dialogue",
        action="translate",
    )


def test_background_stage_converts_bbox_to_a_list(tmp_path: Path, monkeypatch) -> None:
    captured = {}

    def fake_build(folder, image_bytes, composite, regions, width, height):
        captured["regions"] = regions
        return {"counts": {"bubbles": 1, "sam": 1, "box_fallback": 0, "fallback_suppressed": False}, "usage": None}

    monkeypatch.setattr(job_module, "build_assets", fake_build)
    job = job_module.PageJob(id="bbox", register="egyptian", width=200, height=200)
    job_module._background_stage(
        job,
        tmp_path,
        b"x",
        Image.new("RGB", (200, 200), "white"),
        [_region()],
        200,
        200,
    )
    assert captured["regions"][0]["bbox"] == [10, 20, 110, 60]
    assert job.stages[-1].name == "background"


def test_full_job_survives_injected_background_failure(tmp_path: Path, monkeypatch) -> None:
    region = _region()
    mask = Image.new("L", (200, 200), 0)
    mask.paste(255, (10, 20, 110, 60))

    monkeypatch.setattr(job_module, "JOBS_DIR", tmp_path)
    monkeypatch.setattr(
        job_module.regions_stage,
        "read_regions",
        lambda *a, **k: ([region], SimpleNamespace(spark_cost=lambda: 0.0, to_dict=lambda: {})),
    )
    monkeypatch.setattr(job_module, "dedupe_regions", lambda regions: regions)
    monkeypatch.setattr(
        job_module.segment_stage,
        "segment_regions",
        lambda *a, **k: ({"t1": mask}, SimpleNamespace(images=0), []),
    )
    buffer = io.BytesIO()
    Image.new("RGB", (200, 200), "white").save(buffer, format="PNG")
    plate_bytes = buffer.getvalue()
    monkeypatch.setattr(job_module.plate_stage, "clean_plate", lambda *a, **k: (plate_bytes, None))
    monkeypatch.setattr(job_module.plate_stage, "estimate_shift", lambda *a, **k: (0, 0))
    monkeypatch.setattr(job_module.plate_stage, "apply_shift", lambda image, size, dx, dy: image)
    monkeypatch.setattr(job_module.plate_stage, "alignment_report", lambda *a, **k: {"mean_diff": 0.0})
    monkeypatch.setattr(job_module.coverage_stage, "coverage_for", lambda *a, **k: (mask, 100))
    monkeypatch.setattr(job_module.leaders_stage, "find_leaders", lambda *a, **k: None)
    monkeypatch.setattr(job_module, "_check", lambda *a, **k: ([], 0.0, {"notes": {}, "verdicts": []}))
    monkeypatch.setattr(job_module, "family_for", lambda *a, **k: "Tajawal")
    monkeypatch.setattr(
        job_module.typeset,
        "fit_text",
        lambda *a, **k: SimpleNamespace(lines=[], size=14, overflow=False),
    )
    monkeypatch.setattr(job_module.render_stage, "contrast_color", lambda *a, **k: (0, 0, 0))
    monkeypatch.setattr(job_module.render_stage, "draw_regions", lambda image, *a, **k: image.copy())
    monkeypatch.setattr(
        job_module.selfcheck_stage,
        "check_render",
        lambda *a, **k: ([], SimpleNamespace(spark_cost=lambda: 0.0), None),
    )
    monkeypatch.setattr(job_module.selfcheck_stage, "apply_fix", lambda *a, **k: None)

    def boom(*_args, **_kwargs):
        raise RuntimeError("injected background failure")

    monkeypatch.setattr(job_module, "build_assets", boom)

    receipt = job_module.run_page_job(plate_bytes, register="egyptian", background_layers=True).to_dict()

    assert receipt["warnings"] and "background layers unavailable" in receipt["warnings"][0]
    background = next(stage for stage in receipt["stages"] if stage["name"] == "background")
    assert "injected background failure" in background["error"]
    assert receipt["artifacts"].get("output")
