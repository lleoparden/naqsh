"""Demo mode: cache hit replays; unknown bytes need explicit LIVE_MODE=1."""

import json
import random
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app, mode_banner
from app.pipeline import demo, document as document_module
from app.pipeline.job import JOBS_DIR

REPO = Path(__file__).resolve().parents[2]
DEMO = REPO / "fixtures" / "demo"
FIXTURE = REPO / "assets" / "generated" / "fixtures" / "01-comic-flat.png"


def entry() -> dict:
    return json.loads((DEMO / "manifest.json").read_text(encoding="utf-8"))[0]


@pytest.fixture()
def demo_on():
    previous = settings.demo_mode
    object.__setattr__(settings, "demo_mode", True)
    yield
    object.__setattr__(settings, "demo_mode", previous)


def test_known_fixture_is_found_by_hash() -> None:
    found = demo.find(FIXTURE.read_bytes())
    assert found is not None
    assert found["name"] == "comic"


def test_unknown_bytes_are_not_a_demo_hit() -> None:
    assert demo.find(bytes(random.getrandbits(8) for _ in range(4096))) is None


def test_materialised_job_keeps_the_recorded_numbers() -> None:
    cache = entry()
    receipt = demo.materialise(cache)
    assert receipt is not None
    assert receipt["demo"] is True
    assert receipt["total_ms"] == cache["total_ms"]
    assert receipt["total_cost_usd"] == cache["total_cost_usd"]
    folder = JOBS_DIR / receipt["id"]
    cached_document = json.loads((DEMO / cache["name"] / "document.json").read_text(encoding="utf-8"))
    rebuilt = document_module.load_document(folder, receipt)
    assert [(layer.id, layer.source_text) for layer in rebuilt.layers if layer.kind == "text"] == [
        (layer["id"], layer["source_text"]) for layer in cached_document["layers"]
    ]
    for name in ("source.png", "composite.png", "output.png"):
        assert (folder / name).is_file()


def test_demo_replay_of_retranslate_returns_cached_msa() -> None:
    cache = entry()
    receipt = demo.materialise(cache)
    folder = JOBS_DIR / receipt["id"]
    document = document_module.load_document(folder, receipt)
    text_layer = next(layer for layer in document.layers if layer.kind == "text")
    cached = json.loads((DEMO / cache["name"] / "document.json").read_text(encoding="utf-8"))
    expected = next(layer for layer in cached["layers"] if layer["id"] == text_layer.id)["arabic"]["msa"]
    assert demo.replay_retranslate(document, text_layer.id, "msa") == expected
    assert demo.replay_retranslate(document, "nope", "msa") is None


def test_localize_replays_a_known_fixture_without_a_key(demo_on) -> None:
    client = TestClient(app)
    response = client.post(
        "/api/localize",
        files={"image": ("comic.png", FIXTURE.read_bytes(), "image/png")},
        data={"register": "egyptian"},
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["demo"] is True
    cache = entry()
    assert payload["total_ms"] == cache["total_ms"]
    assert len(payload["regions"]) == cache["regions"]


def test_localize_unknown_image_is_rejected_without_live_mode(demo_on, monkeypatch) -> None:
    client = TestClient(app)
    from PIL import Image
    import io

    def live_path(raw: bytes, register: str, **kwargs):
        raise AssertionError("paid pipeline must not be reached without LIVE_MODE=1")

    monkeypatch.setattr("app.main.job_module.run_page_job", live_path)
    object.__setattr__(settings, "api_key", "test-key")
    try:
        buffer = io.BytesIO()
        Image.new("RGB", (64, 64), (200, 30, 30)).save(buffer, format="PNG")
        response = client.post(
            "/api/localize",
            files={"image": ("unknown.png", buffer.getvalue(), "image/png")},
            data={"register": "egyptian"},
        )
    finally:
        object.__setattr__(settings, "api_key", "")
    assert response.status_code == 403
    assert "LIVE_MODE=1" in response.json()["detail"]


def test_localize_unknown_image_runs_when_live_mode_is_on(demo_on, monkeypatch) -> None:
    client = TestClient(app)
    from PIL import Image
    import io

    def live_path(raw: bytes, register: str, **kwargs):
        raise ValueError("live path reached")

    monkeypatch.setattr("app.main.job_module.run_page_job", live_path)
    object.__setattr__(settings, "live_mode", True)
    object.__setattr__(settings, "api_key", "test-key")
    try:
        buffer = io.BytesIO()
        Image.new("RGB", (64, 64), (200, 30, 30)).save(buffer, format="PNG")
        response = client.post(
            "/api/localize",
            files={"image": ("unknown.png", buffer.getvalue(), "image/png")},
            data={"register": "egyptian"},
        )
    finally:
        object.__setattr__(settings, "api_key", "")
    assert response.status_code == 422
    assert "live path reached" in response.json()["detail"]


def test_mode_banner_names_the_mode() -> None:
    previous = settings.live_mode
    try:
        object.__setattr__(settings, "live_mode", False)
        assert "DEMO MODE" in mode_banner() and "BLOCKED" in mode_banner()
        object.__setattr__(settings, "live_mode", True)
        assert "LIVE MODE" in mode_banner() and "ENABLED" in mode_banner()
    finally:
        object.__setattr__(settings, "live_mode", previous)


def test_localize_passes_background_layers_flag(demo_on, monkeypatch) -> None:
    client = TestClient(app)
    from PIL import Image
    import io

    captured = {}

    class FakeJob:
        def to_dict(self):
            return {"id": "fake"}

    def fake_job(raw: bytes, register: str, *, background_layers: bool = True):
        captured["background_layers"] = background_layers
        return FakeJob()

    monkeypatch.setattr("app.main.job_module.run_page_job", fake_job)
    object.__setattr__(settings, "live_mode", True)
    object.__setattr__(settings, "api_key", "test-key")
    try:
        buffer = io.BytesIO()
        Image.new("RGB", (64, 64), (10, 120, 60)).save(buffer, format="PNG")
        response = client.post(
            "/api/localize",
            files={"image": ("unknown.png", buffer.getvalue(), "image/png")},
            data={"register": "egyptian", "background_layers": "false"},
        )
    finally:
        object.__setattr__(settings, "api_key", "")
        object.__setattr__(settings, "live_mode", False)
    assert response.status_code == 200
    assert captured["background_layers"] is False
