"""Build the demo cache from real, already-paid job runs.

For each curated fixture: verify a real run exists, rebuild its editable document
from the receipt (so a previous demo edit cannot leak in), and write a compact copy
under ``fixtures/demo/<name>``:

- ``receipt.json``  the real job receipt, timings and cost untouched
- ``document.json`` the editable document (regions, both registers, lines)
- ``plate.webp``    lossless copy of the cleaned composite
- ``source.jpg``    the uploaded page, high quality, for the before/after slider
- ``masks.zip``     the per-region SAM masks
- ``manifest.json`` (root) maps the fixture's SHA-256 to its cache entry

Output PNGs are not stored: the demo loader re-renders them from the document.

Usage: python backend/scripts/build_demo_cache.py
"""

from __future__ import annotations

import hashlib
import json
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PIL import Image  # noqa: E402

from app.pipeline import document as document_module  # noqa: E402
from app.pipeline.job import JOBS_DIR, load_job  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
FIXTURES = REPO / "assets" / "generated" / "fixtures"
OUT = REPO / "fixtures" / "demo"

# name -> (real job id, fixture file, what it is for)
CURATED = {
    "comic": ("7e997e7b7e9f", "01-comic-flat.png", "flat comic page, three regions"),
    "menu": ("9b6f89fbc2b3", "03-menu-paper.png", "dense menu with prices and leaders"),
    "chalkboard": ("79753c06d42e", "04-chalkboard.png", "chalk text on a dark board"),
    "sfx-comic": ("3d06d47ba521", "07-comic-sfx.png", "captions plus a kept sound effect"),
    "label-fail": ("f6d1bc33524b", "05-label-kraft.png", "photo label, plate failure (honest limit)"),
    "phase1-baker": ("4fca92652b05", "assets/generated/test-panel.png", "final PAGE_A: Phase 1 baker comic"),
    "comic-v4": ("81a193834757", "fixtures/demo-v4/pages/comic-a.jpg", "final PAGE_B: Muse-text comic with 3 bubbles + caption"),
    "zion-limit": ("4b1912cbcd74", r"L:\naqsh-review\demo-v3\sources\Zion_National_Park__Ranger_Naturalist_Service_LCCN2007676134.jpg", "final LIMITS: Zion WPA poster (PD)"),
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build(name: str, job_id: str, fixture: str, note: str) -> dict:
    receipt = load_job(job_id)
    if receipt is None:
        raise SystemExit(f"{name}: job {job_id} not found")
    folder = JOBS_DIR / job_id
    target = OUT / name
    target.mkdir(parents=True, exist_ok=True)

    # Canonical document from the receipt, not whatever edits were left on disk.
    document = document_module.layout_document(document_module.document_from_job(receipt))
    (target / "receipt.json").write_text(json.dumps(receipt, indent=2, ensure_ascii=False), encoding="utf-8")
    (target / "document.json").write_text(
        json.dumps(document.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8"
    )

    composite = Image.open(folder / "composite.png").convert("RGB")
    composite.save(target / "plate.webp", "WEBP", lossless=True, method=4)
    source = Image.open(folder / "source.png").convert("RGB")
    source.save(target / "source.jpg", "JPEG", quality=90, optimize=True)

    with zipfile.ZipFile(target / "masks.zip", "w", zipfile.ZIP_DEFLATED) as archive:
        for mask in sorted(folder.glob("mask-*.png")):
            archive.write(mask, mask.name)

    files = {
        "receipt": "receipt.json",
        "document": "document.json",
        "plate": "plate.webp",
        "source": "source.jpg",
        "masks": "masks.zip",
    }
    background_path = folder / "background.json"
    background_counts = {}
    if background_path.is_file():
        background = json.loads(background_path.read_text(encoding="utf-8"))
        scene = background.get("scene")
        if scene and (folder / scene).is_file():
            Image.open(folder / scene).convert("RGBA").save(target / "scene.webp", "WEBP", lossless=True, method=4)
            background["scene"] = "scene.webp"
            with zipfile.ZipFile(target / "background.zip", "w", zipfile.ZIP_DEFLATED) as archive:
                archive.writestr("background.json", json.dumps(background, indent=2, ensure_ascii=False))
                archive.write(target / "scene.webp", "scene.webp")
                for bubble in background.get("bubbles") or []:
                    asset = bubble.get("asset")
                    if asset and (folder / asset).is_file():
                        archive.write(folder / asset, asset)
            (target / "scene.webp").unlink()
            files["background"] = "background.zip"
            background_counts = {
                "bubbles": background.get("bubbles") and len(background["bubbles"]) or 0,
                "sam": sum(1 for bubble in background.get("bubbles") or [] if bubble.get("source") == "sam"),
                "box_fallback": sum(1 for bubble in background.get("bubbles") or [] if bubble.get("source") == "box_fallback"),
                "fallback_suppressed": bool((background.get("counts") or {}).get("fallback_suppressed")),
            }

    fixture_path = Path(fixture) if Path(fixture).is_absolute() else (REPO / fixture if (REPO / fixture).exists() else FIXTURES / fixture)
    entry = {
        "name": name,
        "note": note,
        "fixture": fixture,
        "sha256": sha256(fixture_path),
        "job_id": job_id,
        "width": int(receipt["width"]),
        "height": int(receipt["height"]),
        "regions": len(receipt.get("regions") or []),
        "total_ms": receipt.get("total_ms"),
        "total_cost_usd": receipt.get("total_cost_usd"),
        "recorded_stages": [
            {"name": stage.get("name"), "ms": stage.get("ms"), "cost_usd": stage.get("cost_usd")}
            for stage in receipt.get("stages") or []
        ],
        "files": files,
        "background": background_counts,
        "exported": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
    }
    print(name, f"{entry['regions']} regions", f"{entry['total_ms']} ms", f"${entry['total_cost_usd']:.4f}")
    return entry


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    only = {part.strip() for part in (sys.argv[1] if len(sys.argv) > 1 else "").split(",") if part.strip()}
    manifest = []
    existing = []
    if (OUT / "manifest.json").is_file():
        existing = json.loads((OUT / "manifest.json").read_text(encoding="utf-8"))
    for name, (job_id, fixture, note) in CURATED.items():
        if only and name not in only:
            kept = next((entry for entry in existing if entry.get("name") == name), None)
            if kept:
                manifest.append(kept)
            continue
        manifest.append(build(name, job_id, fixture, note))
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    total = sum(path.stat().st_size for path in OUT.rglob("*") if path.is_file())
    print(f"manifest: {len(manifest)} fixtures, {total / 1e6:.2f} MB")


if __name__ == "__main__":
    main()
