"""Cross-platform demo smoke test: start the backend in demo mode, replay one fixture.

No API key, no paid calls. Run from the repo root or backend; exits non-zero on failure.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import requests

REPO = Path(__file__).resolve().parents[2]
BACKEND = REPO / "backend"
FIXTURE = REPO / "assets" / "generated" / "fixtures" / "01-comic-flat.png"
PORT = 8011


def main() -> None:
    env = dict(os.environ)
    env["DEMO_MODE"] = "1"
    env["LIVE_MODE"] = "0"
    env.pop("MODEL_API_KEY", None)
    log_path = REPO / "backend-smoke.log"
    with log_path.open("wb") as log:
        process = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "app.main:app", "--port", str(PORT)],
            cwd=BACKEND,
            env=env,
            stdout=log,
            stderr=subprocess.STDOUT,
        )
        try:
            for _ in range(60):
                try:
                    with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/api/health", timeout=2) as response:
                        if response.status == 200:
                            break
                except Exception:
                    time.sleep(1)
            else:
                raise SystemExit(f"backend did not become healthy; see {log_path}")
            with FIXTURE.open("rb") as handle:
                result = requests.post(
                    f"http://127.0.0.1:{PORT}/api/localize",
                    files={"image": (FIXTURE.name, handle, "image/png")},
                    data={"register": "egyptian"},
                    timeout=120,
                )
            result.raise_for_status()
            receipt = result.json()
            assert receipt.get("demo") is True, f"expected demo replay, got {receipt.get('demo')}"
            assert (receipt.get("total_ms") or 0) > 0, "replay receipt has no timing"
            print(f"DEMO SMOKE OK: {receipt['id']} demo={receipt['demo']} total_ms={receipt['total_ms']}")
        finally:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()


if __name__ == "__main__":
    main()
