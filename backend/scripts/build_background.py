"""Split the cleaned background into a scenery layer and one layer per speech bubble.

SAM 3.1 segments the bubbles with a concept prompt ("speech bubble"). The composite is
cut into:
- ``scene.png``: the whole page with bubble areas transparent,
- ``bubble-<region>.png``: the composite clipped to that bubble, cropped to its box.

They are added to the job document as ``scene`` and ``bubble`` layers, below the text
layers and above nothing else, so the editor and both exporters can toggle them.

Usage: python backend/scripts/build_background.py [job-id ...]
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.pipeline.document import Layer, load_document, save_document
from app.pipeline.job import JOBS_DIR, load_job
from app.pipeline.meta import sam_segment
from app.pipeline.segment import _paste
from app.pipeline.spend import record_spend

REPO = Path(__file__).resolve().parents[2]
DEFAULT_JOBS = ["d3dbface16b8", "e13f9585b24f"]


def _overlap(mask: np.ndarray, box: list[int]) -> float:
    x1, y1, x2, y2 = box
    area = max(1, (x2 - x1) * (y2 - y1))
    return float(mask[y1:y2, x1:x2].sum()) / area


def build(job_id: str) -> dict:
    receipt = load_job(job_id)
    folder = JOBS_DIR / job_id
    document = load_document(folder, receipt)
    width, height = document.width, document.height

    text_layers = [layer for layer in document.layers if layer.kind == "text"]
    candidates = [layer for layer in text_layers if layer.type in ("dialogue", "caption")]
    objects = []
    cost = 0.0
    if candidates:
        source_bytes = (folder / "source.png").read_bytes()
        objects, usage = sam_segment(source_bytes, "speech bubble", image_size=(width, height))
        cost = usage.images * 2.50 / 1000
        record_spend(f"background bubbles {job_id}", cost, kind="segment", objects=len(objects))

    bubble_masks: list[tuple[Image.Image, list[int]]] = []
    for obj in objects:
        mask = _paste(obj, (width, height))
        bbox = mask.getbbox()
        if bbox is None:
            continue
        bubble_masks.append((mask, list(bbox)))

    if not bubble_masks:
        # SAM found no bubbles (menus, posters): scenery only, no fake bubble layers.
        candidates = []

    matched: dict[str, Image.Image] = {}
    used: set[int] = set()
    for layer in candidates:
        best_index, best_score = None, 0.0
        for index, (mask, _bbox) in enumerate(bubble_masks):
            if index in used:
                continue
            score = _overlap(np.asarray(mask, dtype=np.uint8) > 127, layer.box)
            if score > best_score:
                best_index, best_score = index, score
        if best_index is not None and best_score > 0.25:
            matched[layer.id] = bubble_masks[best_index][0]
            used.add(best_index)

    composite = Image.open(folder / "composite.png").convert("RGBA")
    scene = composite.copy()
    scene_alpha = np.asarray(scene)[:, :, 3].copy()
    bubble_assets: dict[str, tuple[str, list[int]]] = {}

    for layer in candidates:
        mask = matched.get(layer.id)
        if mask is None:
            # No SAM bubble: use the region's container as a rectangular patch so every
            # text region still gets a background layer.
            container = layer.box
            mask = Image.new("L", (width, height), 0)
            ImageDraw.Draw(mask).rectangle(container, fill=255)
        mask_np = np.asarray(mask, dtype=np.uint8) > 127
        scene_alpha[mask_np] = 0
        patch = composite.copy()
        patch.putalpha(mask)
        bbox = patch.getbbox() or tuple(layer.box)
        cropped = patch.crop(bbox)
        name = f"bubble-{layer.id}.png"
        cropped.save(folder / name)
        bubble_assets[layer.id] = (name, list(bbox))

    scene.putalpha(Image.fromarray(scene_alpha, mode="L"))
    scene.save(folder / "scene.png")

    keep = [layer for layer in document.layers if layer.kind not in ("scene", "bubble")]
    scene_layer = Layer(
        id="scene",
        kind="scene",
        box=[0, 0, width, height],
        type="background",
        name="Scenery",
        asset="scene.png",
        z=-1000,
        locked=False,
    )
    bubbles = []
    for index, (layer_id, (name, bbox)) in enumerate(bubble_assets.items()):
        text_layer = next(item for item in text_layers if item.id == layer_id)
        bubbles.append(
            Layer(
                id=f"bubble-{layer_id}",
                kind="bubble",
                box=bbox,
                type="bubble",
                name=f"Bubble · {text_layer.name or text_layer.id}",
                asset=name,
                z=-500 + index,
                locked=False,
            )
        )
    document.layers = [scene_layer, *bubbles, *keep]
    save_document(folder, document)
    return {
        "job": job_id,
        "cost_usd": round(cost, 6),
        "bubbles": len(bubbles),
        "sam_objects": len(objects),
        "layers": len(document.layers),
    }


def main() -> None:
    jobs = sys.argv[1:] or DEFAULT_JOBS
    for job_id in jobs:
        print(build(job_id))


if __name__ == "__main__":
    main()
