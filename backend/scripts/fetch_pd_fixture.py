"""Fetch a verified public-domain page from Wikimedia Commons (no generation)."""

from __future__ import annotations

import json
import sys
from datetime import date
from io import BytesIO
from pathlib import Path

import requests
from PIL import Image

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "assets" / "generated" / "fixtures" / "06-real-pd-poster.png"
API = "https://commons.wikimedia.org/w/api.php"
UA = {"User-Agent": "NaqshHackathon/1.0 (educational hackathon; contact: mostafa.ahmed.nabil.eid@gmail.com)"}
TITLE = "File:Cook's Nile and Palestine Tours poster - circa 1902.jpg"


def main() -> None:
    params = {
        "action": "query",
        "format": "json",
        "titles": TITLE,
        "prop": "imageinfo",
        "iiprop": "url|extmetadata|size",
    }
    meta = requests.get(API, params=params, headers=UA, timeout=40).json()
    page = next(iter(meta["query"]["pages"].values()))
    info = page["imageinfo"][0]
    fields = info["extmetadata"]
    license_name = fields.get("LicenseShortName", {}).get("value", "")
    usage = fields.get("UsageTerms", {}).get("value", "")
    artist = fields.get("Artist", {}).get("value", "")
    credit = fields.get("Credit", {}).get("value", "")
    record = {
        "title": page["title"],
        "page_url": "https://commons.wikimedia.org/wiki/" + page["title"].replace(" ", "_"),
        "file_url": info["url"],
        "license": license_name,
        "usage_terms": usage,
        "artist": artist,
        "credit": credit,
        "accessed": date.today().isoformat(),
        "size": [info["width"], info["height"]],
    }
    if "public domain" not in license_name.lower() and "cc0" not in license_name.lower():
        print(json.dumps({"error": "license not PD/CC0", **record}, indent=2))
        sys.exit(1)

    image = Image.open(BytesIO(requests.get(info["url"], headers=UA, timeout=120).content)).convert("RGB")
    image.thumbnail((1600, 1600), Image.LANCZOS)
    image.save(OUT)
    record["saved"] = str(OUT.relative_to(REPO))
    record["saved_size"] = list(image.size)
    (OUT.parent / "06-real-pd-poster.json").write_text(json.dumps(record, indent=2), encoding="utf-8")
    print(json.dumps(record, indent=2))


if __name__ == "__main__":
    main()
