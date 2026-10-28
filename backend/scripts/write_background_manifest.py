"""Write background.json manifests from existing scene/bubble layers (no API calls)."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.pipeline.job import JOBS_DIR

JOBS = ["d3dbface16b8", "e13f9585b24f"]

for job_id in JOBS:
    folder = JOBS_DIR / job_id
    path = folder / "document.json"
    if not path.is_file():
        print(job_id, "no document")
        continue
    document = json.loads(path.read_text(encoding="utf-8"))
    layers = document["layers"]
    scene = next((layer for layer in layers if layer["kind"] == "scene"), None)
    if scene is None:
        print(job_id, "no scene layer")
        continue
    manifest = {
        "scene": scene.get("asset"),
        "bubbles": [
            {
                "id": layer["id"],
                "box": layer["box"],
                "asset": layer.get("asset"),
                "name": layer.get("name"),
            }
            for layer in layers
            if layer["kind"] == "bubble"
        ],
    }
    (folder / "background.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(job_id, "bubbles", len(manifest["bubbles"]))
