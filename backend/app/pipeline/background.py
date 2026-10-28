"""Background layers built from the pipeline result.

For a page with dialogue/caption regions:
- SAM 3.1 segments the speech bubbles with one concept call,
- every bubble is cut from the cleaned composite into its own PNG,
- the composite is written as ``scene.png`` with the bubble areas transparent,
- ``background.json`` records each bubble's box, asset and **source**
  (``sam`` when the mask came from SAM, ``box_fallback`` when the reading box was used).

The editor/exporter attach these layers from ``background.json``.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageDraw

from .meta import sam_segment
from .segment import _paste

BUBBLE_TYPES = {"dialogue", "caption"}
MIN_OVERLAP = 0.25


def _overlap(mask: np.ndarray, box: list[int]) -> float:
    x1, y1, x2, y2 = box
    area = max(1, (x2 - x1) * (y2 - y1))
    return float(mask[y1:y2, x1:x2].sum()) / area


def build_assets(
    folder: Path,
    source_bytes: bytes,
    composite: Image.Image,
    regions: list[dict[str, Any]],
    width: int,
    height: int,
) -> dict[str, Any]:
    """Write scene/bubble assets + background.json. Returns counts and SAM usage."""
    candidates = [region for region in regions if str(region.get("type") or "") in BUBBLE_TYPES]
    composite = composite.convert("RGBA")
    scene = composite.copy()
    scene_alpha = np.asarray(scene)[:, :, 3].copy()
    bubbles: list[dict[str, Any]] = []
    usage = None

    suppressed = False
    if candidates:
        objects, usage = sam_segment(source_bytes, "speech bubble", image_size=(width, height))
        masks: list[tuple[Image.Image, dict[str, Any]]] = []
        for obj in objects:
            mask = _paste(obj, (width, height))
            if mask.getbbox() is not None:
                masks.append((mask, obj))
        if not masks:
            # No bubble detected on this page: no bubble layers at all, even if some
            # regions are typed as dialogue/caption. Scenery only.
            candidates = []
            suppressed = True

        matched: dict[str, Image.Image] = {}
        used: set[int] = set()
        for region in candidates:
            best_index, best_score = None, 0.0
            box = [int(v) for v in region["bbox"]]
            for index, (mask, _obj) in enumerate(masks):
                if index in used:
                    continue
                score = _overlap(np.asarray(mask, dtype=np.uint8) > 127, box)
                if score > best_score:
                    best_index, best_score = index, score
            if best_index is not None and best_score > MIN_OVERLAP:
                matched[region["id"]] = masks[best_index][0]
                used.add(best_index)

        for region in candidates:
            region_id = str(region["id"])
            box = [int(v) for v in region["bbox"]]
            mask = matched.get(region_id)
            source = "sam"
            if mask is None:
                mask = Image.new("L", (width, height), 0)
                ImageDraw.Draw(mask).rectangle(box, fill=255)
                source = "box_fallback"
            mask_np = np.asarray(mask, dtype=np.uint8) > 127
            scene_alpha[mask_np] = 0
            patch = composite.copy()
            patch.putalpha(mask)
            bbox = patch.getbbox() or tuple(box)
            asset = f"bubble-{region_id}.png"
            patch.crop(bbox).save(folder / asset)
            bubbles.append(
                {
                    "id": f"bubble-{region_id}",
                    "region": region_id,
                    "box": list(bbox),
                    "asset": asset,
                    "name": f"Bubble · {region.get('name') or region_id}",
                    "source": source,
                }
            )

    scene.putalpha(Image.fromarray(scene_alpha, mode="L"))
    scene.save(folder / "scene.png")
    counts = {
        "bubbles": len(bubbles),
        "sam": sum(1 for bubble in bubbles if bubble["source"] == "sam"),
        "box_fallback": sum(1 for bubble in bubbles if bubble["source"] == "box_fallback"),
        "fallback_suppressed": suppressed,
    }
    manifest = {
        "scene": "scene.png",
        "bubbles": bubbles,
        "counts": counts,
    }
    (folder / "background.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    return {"counts": counts, "usage": usage, "candidates": len(candidates)}
