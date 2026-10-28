"""Group 1 backend: reset-to-AI, size clamp, retranslate throttle."""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.pipeline import throttle


@pytest.fixture()
def client():
    throttle.reset()
    return TestClient(app)


def test_throttle_blocks_two_in_flight_calls() -> None:
    assert throttle.acquire("job", "t1") is None
    assert throttle.acquire("job", "t1") == "in_flight"
    throttle.release("job", "t1")
    assert throttle.acquire("job", "t1") is None


def test_throttle_rate_limits_a_job() -> None:
    for index in range(6):
        assert throttle.acquire("job2", f"t{index}") is None
        throttle.release("job2", f"t{index}")
    assert throttle.acquire("job2", "t99") == "rate_limited"


def test_layout_clamps_font_size(client) -> None:
    from app.pipeline.demo import materialise, load_manifest

    entry = load_manifest()[0]
    receipt = materialise(entry)
    job_id = receipt["id"]
    response = client.post(f"/api/jobs/{job_id}/layout", json={"layer_id": "t1", "font_size": 5000})
    assert response.status_code == 200
    assert response.json()["layer"]["font_size"] <= 1000


def test_reset_restores_the_first_ai_result(client) -> None:
    from app.pipeline.demo import materialise, load_manifest

    entry = load_manifest()[0]
    receipt = materialise(entry)
    job_id = receipt["id"]
    before = client.get(f"/api/jobs/{job_id}/document").json()
    layer = next(item for item in before["layers"] if item["kind"] == "text")
    original = layer["original"]
    assert original, "first AI result must be snapshotted"

    patched = client.patch(
        f"/api/jobs/{job_id}/document",
        json={"layers": [{"id": layer["id"], "arabic": {"egyptian": "نص مختلف"}, "font_family": "naskh", "color": [255, 0, 0]}]},
    )
    assert patched.status_code == 200

    reset = client.post(f"/api/jobs/{job_id}/reset-region", json={"layer_id": layer["id"]})
    assert reset.status_code == 200, reset.text
    restored = reset.json()["layer"]
    assert restored["arabic"]["egyptian"] == original["arabic"]["egyptian"]
    assert restored["font_family"] == original["font_family"]
    assert restored["color"] == original["color"]
    assert restored["box"] == original["box"]
