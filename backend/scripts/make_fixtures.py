"""Generate the Phase 4 gate pages with Muse Image (rights-clean by construction).

Five pages with deliberately different backgrounds: flat comic art, watercolour
paper, printed menu paper, chalkboard, kraft label. The manifest records each
prompt so the pages can be regenerated and so ASSETS.md can cite them.

Usage: python backend/scripts/make_fixtures.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.pipeline.meta import image_generate  # noqa: E402

OUT = Path(__file__).resolve().parents[2] / "assets" / "generated" / "fixtures"

FIXTURES: list[dict[str, str]] = [
    {
        "name": "01-comic-flat",
        "note": "Flat vector comic page — already the Phase 2 test panel; copied here as fixture 1.",
        "source": "../test-panel.png",
        "prompt": "(copied from assets/generated/test-panel.png — bakery comic page with three text regions)",
    },
    {
        "name": "02-poster-watercolour",
        "note": "Textured watercolour poster: text sits on painted texture, not flat fill.",
        "prompt": (
            "A vintage travel poster of the Alexandria corniche at sunset, painted in loose "
            "watercolour with visible paper grain and pigment blooms, warm ochre and teal. "
            "Large title lettering 'ALEXANDRIA' across the top, a smaller line "
            "'THE PEARL OF THE MEDITERRANEAN' beneath it, and a small caption 'EST. 331 BC' at "
            "the bottom. Original artwork, no signature, portrait orientation."
        ),
        "size": "1024x1536",
    },
    {
        "name": "03-menu-paper",
        "note": "Dense menu on printed paper: many small text lines, paper texture behind.",
        "prompt": (
            "A printed restaurant menu on warm cream paper with a subtle fibrous texture and "
            "faint coffee stain in one corner. Heading 'KOSHARY HOUSE' in bold lettering, then "
            "a list of dishes with prices in two columns: 'KOSHARY 45', 'FALAFEL 20', "
            "'MINT TEA 10', 'BASBOUSA 30', 'LENTIL SOUP 25', 'RICE PUDDING 30'. Simple red and "
            "black ink, no photographs, portrait orientation, original design."
        ),
        "size": "1024x1536",
    },
    {
        "name": "04-chalkboard",
        "note": "Chalkboard: chalk texture and uneven strokes; text is light on dark.",
        "prompt": (
            "A cafe chalkboard sign photographed straight on, dark slate surface with chalk "
            "dust and smudges, wooden frame at the edges. Chalk lettering reads 'TODAY'S "
            "SPECIAL' across the top, then 'MINT TEA 25' and 'BASBOUSA 30' with a small "
            "hand-drawn star. Original sign, portrait orientation, no brand names."
        ),
        "size": "1024x1536",
    },
    {
        "name": "05-label-kraft",
        "note": "Small print on a kraft-paper label: low contrast, textured stock.",
        "prompt": (
            "A close-up product photograph of a glass spice jar with a kraft-paper label, "
            "visible paper fibres and a soft shadow. The label reads 'CUMIN' in a large serif, "
            "'GROUND' in small caps beneath, and 'NET 100 G' at the bottom. Warm daylight, "
            "shallow depth of field, no other branding, portrait orientation."
        ),
        "size": "1024x1536",
    },
]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    manifest: list[dict[str, str]] = []
    for item in FIXTURES:
        target = OUT / f"{item['name']}.png"
        if item.get("source"):
            source = (OUT / item["source"]).resolve()
            target.write_bytes(source.read_bytes())
            entry = {**item, "path": str(target.relative_to(OUT.parents[2])), "generated": "copied"}
        else:
            png, _usage = image_generate(item["prompt"], size=item.get("size", "1024x1536"))
            target.write_bytes(png)
            entry = {**item, "path": str(target.relative_to(OUT.parents[2])), "generated": "muse-image-1.0"}
        manifest.append(entry)
        print(f"{item['name']}: {target.stat().st_size} bytes")

    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {OUT / 'manifest.json'}")


if __name__ == "__main__":
    main()
