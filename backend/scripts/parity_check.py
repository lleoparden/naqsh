"""Parity: server render vs browser render of the same layered SVG.

Browsers shape Arabic with HarfBuzz, the same engine the server uses, so the SVG
should match the server PNG if the fonts are available. This wraps the SVG in an HTML
page with @font-face pointing at the bundled OFL fonts (base64), screenshots it with
headless Chrome, and diffs the result against the server render.

Usage: python backend/scripts/parity_check.py <job-id> [<job-id> ...]
"""

from __future__ import annotations

import base64
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.pipeline import document as document_module  # noqa: E402
from app.pipeline import export as export_module  # noqa: E402
from app.pipeline import shaping  # noqa: E402
from app.pipeline.job import JOBS_DIR, load_job  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
EVIDENCE = REPO / "docs" / "evidence" / "phase-6"
CHROME = Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")

FACES = [
    ("Tajawal", 400, "Tajawal-Regular.ttf"),
    ("Tajawal", 700, "Tajawal-Bold.ttf"),
    ("Noto Naskh Arabic", 400, "NotoNaskhArabic-Variable.ttf"),
    ("Amiri", 400, "Amiri-Regular.ttf"),
]


def _font_css() -> str:
    rules = []
    for family, weight, file_name in FACES:
        data = (shaping.FONT_DIR / file_name).read_bytes()
        encoded = base64.b64encode(data).decode("ascii")
        rules.append(
            f"@font-face {{ font-family: '{family}'; font-weight: {weight}; "
            f"src: url(data:font/ttf;base64,{encoded}) format('truetype'); }}"
        )
    return "\n".join(rules)


def render_browser(svg: str, width: int, height: int, out_png: Path) -> None:
    html = (
        "<!doctype html><html><head><meta charset='utf-8'><style>"
        "html,body{margin:0;padding:0;background:#fff;}"
        f"{_font_css()}"
        "</style></head><body>"
        f"{svg}"
        "</body></html>"
    )
    with tempfile.TemporaryDirectory() as tmp:
        page = Path(tmp) / "page.html"
        page.write_text(html, encoding="utf-8")
        subprocess.run(
            [
                str(CHROME),
                "--headless=new",
                "--disable-gpu",
                "--hide-scrollbars",
                f"--window-size={width},{height}",
                "--virtual-time-budget=4000",
                f"--screenshot={out_png}",
                page.as_uri(),
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )


def main() -> None:
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    results = []
    for job_id in sys.argv[1:]:
        receipt = load_job(job_id)
        folder = JOBS_DIR / job_id
        doc = document_module.load_document(folder, receipt)
        server = export_module.render_png(doc, folder)
        svg = export_module.build_svg(doc, folder)
        browser_png = EVIDENCE / f"parity-{job_id}-browser.png"
        render_browser(svg, doc.width, doc.height, browser_png)
        browser = Image.open(browser_png).convert("RGB").resize(server.size)
        a = np.asarray(server, dtype=np.int16)
        b = np.asarray(browser, dtype=np.int16)
        diff = np.abs(a - b).max(axis=2)
        result = {
            "job": job_id,
            "server_png": str((EVIDENCE / f"parity-{job_id}-server.png")),
            "browser_png": str(browser_png),
            "mean_abs_diff": round(float(diff.mean()), 2),
            "pixels_over_40": round(float((diff > 40).mean() * 100), 3),
            "pixels_over_80": round(float((diff > 80).mean() * 100), 3),
        }
        server.save(EVIDENCE / f"parity-{job_id}-server.png")
        Image.fromarray(np.clip(diff * 2, 0, 255).astype("uint8")).save(EVIDENCE / f"parity-{job_id}-diff.png")
        results.append(result)
        print(json.dumps(result))
    (EVIDENCE / "parity.json").write_text(json.dumps(results, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
