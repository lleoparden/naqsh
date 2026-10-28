"""Demo mode: replay a recorded real run for a known fixture.

The cache lives in ``fixtures/demo`` and holds, per fixture, the real receipt (stage
timings and cost untouched), the editable document, the cleaned plate, the uploaded
source and the SAM masks. On a cache hit the job is materialised into the normal job
store, so every existing endpoint (files, document, layout, export) works unchanged,
and the response carries ``demo: true`` plus the recorded timings.

Anything that is not a byte-for-byte match for a cached fixture goes to the live
pipeline. The cache is a recording aid, never a replacement for a live run.
"""

from __future__ import annotations

import hashlib
import io
import json
import shutil
import uuid
import zipfile
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw

from . import document as document_module
from . import export as export_module
from .job import JOBS_DIR

REPO = Path(__file__).resolve().parents[3]
DEMO_DIR = REPO / "fixtures" / "demo"
MANIFEST = DEMO_DIR / "manifest.json"


def load_manifest() -> list[dict[str, Any]]:
    if not MANIFEST.is_file():
        return []
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def find(raw: bytes) -> dict[str, Any] | None:
    """Return the cache entry whose fixture hashes to exactly these bytes."""
    digest = hashlib.sha256(raw).hexdigest()
    return next((entry for entry in load_manifest() if entry.get("sha256") == digest), None)


def _write_before_after(source: Image.Image, output: Image.Image, path: Path) -> None:
    gap = 16
    width = source.width + output.width + gap
    height = max(source.height, output.height)
    sheet = Image.new("RGB", (width, height), (246, 241, 231))
    sheet.paste(source, (0, 0))
    sheet.paste(output, (source.width + gap, 0))
    draw = ImageDraw.Draw(sheet)
    draw.text((12, 12), "before", fill=(255, 255, 255))
    draw.text((source.width + gap + 12, 12), "after", fill=(255, 255, 255))
    sheet.save(path)


def materialise(entry: dict[str, Any]) -> dict[str, Any] | None:
    """Build a normal job folder from a cache entry and return its receipt."""
    source_dir = DEMO_DIR / entry["name"]
    receipt_path = source_dir / "receipt.json"
    if not receipt_path.is_file():
        return None
    job_id = f"demo-{uuid.uuid4().hex[:8]}"
    folder = JOBS_DIR / job_id
    folder.mkdir(parents=True, exist_ok=True)

    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["id"] = job_id
    receipt["demo"] = True
    receipt["demo_source"] = entry["name"]
    receipt["demo_note"] = "replaying a recorded real run"
    receipt["demo_recorded_job"] = entry.get("job_id")
    receipt["demo_recorded_stages"] = entry.get("recorded_stages") or []

    plate = Image.open(source_dir / entry["files"]["plate"]).convert("RGB")
    plate.save(folder / "composite.png")
    source = Image.open(source_dir / entry["files"]["source"]).convert("RGB")
    source.save(folder / "source.png")

    with zipfile.ZipFile(source_dir / entry["files"]["masks"]) as archive:
        archive.extractall(folder)

    background_zip = entry["files"].get("background")
    if background_zip and (source_dir / background_zip).is_file():
        with zipfile.ZipFile(source_dir / background_zip) as archive:
            archive.extractall(folder)

    shutil.copyfile(source_dir / entry["files"]["document"], folder / "document.json")
    document = document_module.load_document(folder, receipt)

    output = export_module.render_png(document, folder)
    output.save(folder / "output.png")
    _write_before_after(source, output, folder / "before-after.png")

    receipt["artifacts"] = {
        "source": "source.png",
        "composite": "composite.png",
        "output": "output.png",
        "before_after": "before-after.png",
        "mask_overlay": "",
    }
    (folder / "job.json").write_text(json.dumps(receipt, indent=2, ensure_ascii=False), encoding="utf-8")
    return receipt


def replay_retranslate(document: document_module.Document, layer_id: str, register: str) -> str | None:
    """The cached Arabic for this layer and register, or None to fall back to live."""
    layer = document.layer(layer_id)
    if layer is None:
        return None
    text = layer.arabic.get(register)
    return text or None
