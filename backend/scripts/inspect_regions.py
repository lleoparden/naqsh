"""Print the regions Spark found for one page (diagnosis only)."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PIL import Image

from app.pipeline.regions import read_regions
from app.pipeline.spend import record_spend

REPO = Path(__file__).resolve().parents[2]
name = sys.argv[1]
path = REPO / "assets" / "generated" / "fixtures" / f"{name}.png"
with Image.open(path) as image:
    width, height = image.size
regions, usage = read_regions(path.read_bytes(), width, height, "egyptian")
record_spend(f"inspect {name}", usage.spark_cost(), kind="read")
print(f"{name}: ${usage.spark_cost():.4f}, {len(regions)} regions")
for region in regions:
    print(f"  {region.id:4s} {region.type:11s} {region.action:13s} {region.source_text!r}")
