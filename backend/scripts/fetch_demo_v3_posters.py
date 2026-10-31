"""Fetch the three public-domain v3 posters from Wikimedia Commons (outside the repo).

Writes to L:\\naqsh-review\\demo-v3\\sources and records SHA-256 in the evidence manifest.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import requests

OUT = Path(r"L:\naqsh-review\demo-v3\sources")
MANIFEST = Path(__file__).resolve().parents[2] / "docs" / "evidence" / "demo-v3-poster-sources.json"
TITLES = [
    "File:Grand Canyon National Park, a free government service LCCN2007676131.jpg",
    "File:Zion National Park, Ranger Naturalist Service LCCN2007676134.jpg",
    "File:Lassen Volcanic National Park, Ranger Naturalist Service LCCN2007676132.tif",
]
API = "https://commons.wikimedia.org/w/api.php"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    for title in TITLES:
        params = {
            "action": "query",
            "titles": title,
            "prop": "imageinfo",
            "iiprop": "url|extmetadata|size",
            "iiurlwidth": "1600",
            "format": "json",
        }
        data = requests.get(API, params=params, timeout=60).json()
        page = next(iter(data["query"]["pages"].values()))
        info = page["imageinfo"][0]
        name = title.removeprefix("File:").replace(" ", "_")
        path = OUT / name
        path.write_bytes(requests.get(info["thumburl"], timeout=120).content)
        meta = info["extmetadata"]
        rows.append(
            {
                "file": name,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "width": info["width"],
                "height": info["height"],
                "title": title,
                "page": info["descriptionurl"],
                "license": meta["LicenseShortName"]["value"],
                "usage": meta["UsageTerms"]["value"],
                "author": meta["Artist"]["value"],
                "credit": meta["Credit"]["value"],
            }
        )
        print(name, rows[-1]["sha256"][:12])
    MANIFEST.write_text(json.dumps({"sources": rows}, indent=2, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
