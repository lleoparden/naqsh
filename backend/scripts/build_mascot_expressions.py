"""Generate idle/thinking/happy expression variants for three distinct mascot concepts."""

from __future__ import annotations

import io
import json
import sys
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.pipeline.meta import image_edit
from app.pipeline.spend import record_spend

REPO = Path(__file__).resolve().parents[2]
CONCEPTS = Path(r"L:\naqsh-review\mascot\concepts")
OUT = Path(r"L:\naqsh-review\mascot\expressions")
MANIFEST = REPO / "docs" / "mascot-manifest.json"
BASES = ["dot-a", "ink-a", "layers"]

PROMPTS = {
    "idle": (
        "Keep this exact mascot character completely unchanged: same silhouette, same colours, same pose, "
        "same plain background, same flat vector style. Change only the face to a calm idle expression with two "
        "tiny dot eyes and a small neutral smile. No text, no letters, no logo, no extra objects."
    ),
    "thinking": (
        "Keep this exact mascot character completely unchanged: same silhouette, same colours, same pose, "
        "same plain background, same flat vector style. Change only the face to a thinking expression: eyes looking "
        "slightly up, a small flat mouth, and three tiny simple dots floating above the head (no text). No letters, "
        "no logo, no extra objects."
    ),
    "happy": (
        "Keep this exact mascot character completely unchanged: same silhouette, same colours, same pose, "
        "same plain background, same flat vector style. Change only the face to a happy expression: closed smiling "
        "eyes (two small arcs) and a small open smile. No text, no letters, no logo, no extra objects."
    ),
}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    data = json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.is_file() else {"concepts": []}
    entries = []
    for base in BASES:
        source = (CONCEPTS / f"{base}.png").read_bytes()
        for state, prompt in PROMPTS.items():
            raw, usage = image_edit(source, prompt)
            cost = (usage.images or 1) * 0.01
            record_spend(f"mascot expression {base} {state}", cost, kind="image")
            image = Image.open(io.BytesIO(raw)).convert("RGB")
            path = OUT / f"{base}-{state}.png"
            image.save(path)
            entries.append(
                {
                    "base": base,
                    "state": state,
                    "prompt": prompt,
                    "file": str(path),
                    "cost_usd": round(cost, 4),
                }
            )
            print("generated", base, state, f"${cost:.2f}")
    data["expressions"] = entries
    MANIFEST.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
