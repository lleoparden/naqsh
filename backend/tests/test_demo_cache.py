"""The demo cache must be complete, real, and traceable."""

import hashlib
import json
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DEMO = REPO / "fixtures" / "demo"
FIXTURES = REPO / "assets" / "generated" / "fixtures"


def manifest() -> list[dict]:
    return json.loads((DEMO / "manifest.json").read_text(encoding="utf-8"))


def test_cache_has_the_curated_pages() -> None:
    names = {entry["name"] for entry in manifest()}
    assert names == {"comic", "menu", "chalkboard", "sfx-comic", "label-fail", "phase1-baker", "comic-v4", "zion-limit"}


def test_every_entry_has_files_and_a_real_hash() -> None:
    for entry in manifest():
        for key in ("receipt", "document", "plate", "source", "masks"):
            assert (DEMO / entry["name"] / entry["files"][key]).is_file(), (entry["name"], key)
        assert len(entry["sha256"]) == 64
        fixture = REPO / entry["fixture"] if (REPO / entry["fixture"]).exists() else FIXTURES / entry["fixture"]
        assert hashlib.sha256(fixture.read_bytes()).hexdigest() == entry["sha256"]


def test_receipts_keep_real_timings_and_cost() -> None:
    for entry in manifest():
        receipt = json.loads((DEMO / entry["name"] / "receipt.json").read_text(encoding="utf-8"))
        assert receipt["total_ms"] > 0
        assert receipt["total_cost_usd"] > 0
        stages = [stage for stage in receipt["stages"] if stage.get("ms")]
        assert stages, entry["name"]
        assert all(stage["ms"] > 0 for stage in stages)
        assert receipt["total_ms"] == entry["total_ms"]
        assert receipt["total_cost_usd"] == entry["total_cost_usd"]


def test_document_regions_match_the_receipt() -> None:
    for entry in manifest():
        receipt = json.loads((DEMO / entry["name"] / "receipt.json").read_text(encoding="utf-8"))
        document = json.loads((DEMO / entry["name"] / "document.json").read_text(encoding="utf-8"))
        assert len(document["layers"]) == len(receipt["regions"])
        assert document["width"] == entry["width"]
        for layer in document["layers"]:
            if layer["kind"] == "text":
                assert layer["arabic"].get("egyptian")


def test_masks_archive_is_not_empty() -> None:
    for entry in manifest():
        with zipfile.ZipFile(DEMO / entry["name"] / "masks.zip") as archive:
            assert archive.namelist(), entry["name"]
