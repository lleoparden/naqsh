"""Phase 6 gate: edit real jobs through the API, export, and compare renders.

Applies the gate edits (change a line, switch one region to MSA, skip one region,
nudge one box, add a cover patch), exports SVG/ZIP/PNG, screenshots the editor and
the exported SVG, and diffs them. Writes JSON evidence.

Usage: python backend/scripts/gate_6.py <job-id> [<job-id> ...]
"""

from __future__ import annotations

import base64
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
import requests
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.pipeline import export as export_module  # noqa: E402
from app.pipeline import shaping  # noqa: E402
from app.pipeline.document import Document  # noqa: E402
from app.pipeline.job import JOBS_DIR, load_job  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
EVIDENCE = REPO / "docs" / "evidence" / "phase-6"
API = "http://127.0.0.1:8010"
CHROME = Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")
FACES = [
    ("Tajawal", 400, "Tajawal-Regular.ttf"),
    ("Tajawal", 700, "Tajawal-Bold.ttf"),
    ("Noto Naskh Arabic", 400, "NotoNaskhArabic-Variable.ttf"),
    ("Amiri", 400, "Amiri-Regular.ttf"),
]


def font_css() -> str:
    rules = []
    for family, weight, file_name in FACES:
        data = base64.b64encode((shaping.FONT_DIR / file_name).read_bytes()).decode("ascii")
        rules.append(
            f"@font-face{{font-family:'{family}';font-weight:{weight};"
            f"src:url(data:font/ttf;base64,{data}) format('truetype');}}"
        )
    return "\n".join(rules)


def render_svg(chrome_svg: str, width: int, height: int, out: Path) -> None:
    html = (
        "<!doctype html><html><head><meta charset='utf-8'><style>"
        f"html,body{{margin:0;background:#fff}}{font_css()}</style></head><body>{chrome_svg}</body></html>"
    )
    with tempfile.TemporaryDirectory() as tmp:
        page = Path(tmp) / "page.html"
        page.write_text(html, encoding="utf-8")
        subprocess.run(
            [str(CHROME), "--headless=new", "--disable-gpu", "--hide-scrollbars",
             f"--window-size={width},{height}", "--virtual-time-budget=5000", f"--screenshot={out}", page.as_uri()],
            check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )


def screenshot(url: str, out: Path, width: int = 1500, height: int = 950) -> None:
    subprocess.run(
        [str(CHROME), "--headless=new", "--disable-gpu", "--hide-scrollbars",
         f"--window-size={width},{height}", "--virtual-time-budget=6000", f"--screenshot={out}", url],
        check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )


def main() -> None:
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    results = []
    for job_id in sys.argv[1:]:
        doc = requests.get(f"{API}/api/jobs/{job_id}/document", timeout=30).json()
        layers = [layer for layer in doc["layers"] if layer["kind"] == "text"]
        if len(layers) < 3:
            print(f"{job_id}: only {len(layers)} text layers, skipping")
            continue
        first, second, third = layers[0], layers[1], layers[2]
        edits = [
            {"id": first["id"], "arabic": {doc["register"]: first["arabic"][doc["register"]] + " جدا"}},
            {"id": third["id"], "action": "skip"},
            {
                "id": second["id"],
                "box": [
                    second["box"][0] + 12,
                    second["box"][1] - 8,
                    second["box"][2] + 12,
                    second["box"][3] - 8,
                ],
            },
        ]
        patch = requests.patch(f"{API}/api/jobs/{job_id}/document", json={"layers": edits}, timeout=30)
        patch.raise_for_status()
        retranslated = requests.post(
            f"{API}/api/jobs/{job_id}/retranslate",
            json={"layer_id": second["id"], "register": "msa"},
            timeout=120,
        )
        cost = 0.0
        if retranslated.ok:
            payload = retranslated.json()
            cost = float(payload.get("cost_usd") or 0)
        # Switch the page to MSA so the retranslated line is the active one.
        # The first edit was written into the starting register; after switching
        # registers, apply a visible edit to the now-active text as well.
        requests.patch(
            f"{API}/api/jobs/{job_id}/document",
            json={"layers": [{"id": first["id"], "arabic": {"msa": first["arabic"]["msa"] + " جدا"}}]},
            timeout=30,
        ).raise_for_status()
        requests.patch(f"{API}/api/jobs/{job_id}/document", json={"register": "msa"}, timeout=30).raise_for_status()
        # Cover patch on a corner of the plate (documented fallback for plate failures).
        cover = requests.post(
            f"{API}/api/jobs/{job_id}/cover",
            json={"box": [30, 30, 120, 90], "fill": [246, 240, 226]},
            timeout=30,
        )
        cover.raise_for_status()

        updated = requests.get(f"{API}/api/jobs/{job_id}/document", timeout=30).json()
        svg = requests.get(f"{API}/api/jobs/{job_id}/export.svg", timeout=60).text
        (EVIDENCE / f"gate-{job_id}.svg").write_text(svg, encoding="utf-8")
        zip_bytes = requests.get(f"{API}/api/jobs/{job_id}/export.zip", timeout=60).content
        (EVIDENCE / f"gate-{job_id}.zip").write_bytes(zip_bytes)
        png_bytes = requests.get(f"{API}/api/jobs/{job_id}/export.png", timeout=120).content
        (EVIDENCE / f"gate-{job_id}-export.png").write_bytes(png_bytes)

        editor_png = EVIDENCE / f"gate-{job_id}-editor.png"
        screenshot(f"http://localhost:4174/?job={job_id}", editor_png)
        svg_png = EVIDENCE / f"gate-{job_id}-svg-render.png"
        render_svg(svg, updated["width"], updated["height"], svg_png)

        server = Image.open(EVIDENCE / f"gate-{job_id}-export.png").convert("RGB")
        browser = Image.open(svg_png).convert("RGB").resize(server.size)
        diff = np.abs(np.asarray(server, dtype=np.int16) - np.asarray(browser, dtype=np.int16)).max(axis=2)
        results.append(
            {
                "job": job_id,
                "retranslate_cost_usd": cost,
                "layers": len(updated["layers"]),
                "text_layers": len([layer for layer in updated["layers"] if layer["kind"] == "text"]),
                "covers": len([layer for layer in updated["layers"] if layer["kind"] == "cover"]),
                "svg_bytes": len(svg),
                "zip_bytes": len(zip_bytes),
                "png_bytes": len(png_bytes),
                "svg_vs_png_mean_abs_diff": round(float(diff.mean()), 2),
                "svg_vs_png_pixels_over_40": round(float((diff > 40).mean() * 100), 3),
                "editor_png": str(editor_png),
                "svg_render_png": str(svg_png),
            }
        )
        print(json.dumps(results[-1]))
    (EVIDENCE / "gate.json").write_text(json.dumps(results, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
