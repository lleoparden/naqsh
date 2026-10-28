"""Group 2 backend: cover shape persistence and ellipse in SVG export."""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.pipeline import throttle


@pytest.fixture()
def client():
    throttle.reset()
    return TestClient(app)


def _demo_job(client: TestClient) -> dict:
    from app.pipeline.demo import load_manifest, materialise

    receipt = materialise(load_manifest()[0])
    assert receipt is not None
    return receipt


def test_cover_patch_shape_is_stored_and_exported(client) -> None:
    receipt = _demo_job(client)
    job_id = receipt["id"]
    response = client.post(
        f"/api/jobs/{job_id}/cover",
        json={"box": [40, 40, 200, 160], "fill": [30, 60, 200], "shape": "ellipse"},
    )
    assert response.status_code == 200, response.text
    cover = [layer for layer in response.json()["layers"] if layer["kind"] == "cover"][-1]
    assert cover["shape"] == "ellipse"
    assert cover["fill"] == [30, 60, 200]

    svg = client.get(f"/api/jobs/{job_id}/export.svg").text
    assert f'<ellipse id="cover-{cover["id"]}"' in svg


def test_patch_can_rename_and_change_shape(client) -> None:
    receipt = _demo_job(client)
    job_id = receipt["id"]
    document = client.get(f"/api/jobs/{job_id}/document").json()
    layer = next(item for item in document["layers"] if item["kind"] == "text")
    patched = client.patch(
        f"/api/jobs/{job_id}/document",
        json={"layers": [{"id": layer["id"], "name": "Title banner"}]},
    )
    assert patched.status_code == 200
    renamed = next(item for item in patched.json()["layers"] if item["id"] == layer["id"])
    assert renamed["name"] == "Title banner"
