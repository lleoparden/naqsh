"""HTTP export check: ZIP layers.json + layers/ match SVG groups and the PNG composite."""

import io
import json
import zipfile
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.main import app

REPO = Path(__file__).resolve().parents[2]
FIXTURE = REPO / "assets" / "generated" / "fixtures" / "01-comic-flat.png"


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


def _demo_job(client: TestClient) -> str:
    response = client.post(
        "/api/localize",
        files={"image": ("comic.png", FIXTURE.read_bytes(), "image/png")},
        data={"register": "egyptian"},
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload.get("demo") is True
    return payload["id"]


def test_zip_layers_match_svg_and_composite(client: TestClient) -> None:
    job_id = _demo_job(client)
    document = client.get(f"/api/jobs/{job_id}/document").json()
    assert any(layer["kind"] == "scene" for layer in document["layers"])
    assert any(layer["kind"] == "bubble" for layer in document["layers"])

    response = client.get(f"/api/jobs/{job_id}/export.zip")
    assert response.status_code == 200
    archive = zipfile.ZipFile(io.BytesIO(response.content))
    names = set(archive.namelist())
    manifest = json.loads(archive.read("layers.json"))
    svg = archive.read("export.svg").decode("utf-8")

    kinds = [layer["kind"] for layer in manifest["layers"]]
    assert "scene" in kinds and "bubble" in kinds and "text" in kinds
    assert 'data-name="Scenery"' in svg
    assert 'id="bubbles"' in svg
    assert 'id="text-layers"' in svg

    for layer in manifest["layers"]:
        if layer["kind"] in ("scene", "bubble"):
            assert layer["asset"], layer
            assert f"layers/{layer['asset']}" in names, layer["asset"]

    # scene + bubbles must reconstruct the composite plate exactly (edges included).
    plate = Image.open(io.BytesIO(archive.read("plate.png"))).convert("RGB")
    composed = Image.new("RGBA", plate.size, (0, 0, 0, 0))
    for layer in manifest["layers"]:
        if layer["kind"] == "scene":
            scene = Image.open(io.BytesIO(archive.read(f"layers/{layer['asset']}"))).convert("RGBA")
            composed.alpha_composite(scene)
        if layer["kind"] == "bubble":
            bubble = Image.open(io.BytesIO(archive.read(f"layers/{layer['asset']}"))).convert("RGBA")
            composed.alpha_composite(bubble, (layer["box"][0], layer["box"][1]))
    on_white = Image.new("RGB", plate.size, "white")
    on_white.paste(composed, mask=composed.split()[3])
    diff = np.abs(np.asarray(on_white, dtype=np.int16) - np.asarray(plate, dtype=np.int16))
    assert int(diff.max()) <= 2, f"composite mismatch {int(diff.max())}"

    png = client.get(f"/api/jobs/{job_id}/export.png")
    assert png.status_code == 200
    with Image.open(io.BytesIO(png.content)) as image:
        assert image.size == (document["width"], document["height"])
