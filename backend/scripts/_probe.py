"""Shared plumbing for the Phase 1 Meta Model API probes.

Design rules:
- stdlib only (plus Pillow/requests already in requirements), so a probe runs on a
  bare checkout;
- the key is read from the repo-root ``.env`` or the environment, and is never
  printed, logged, or written into a receipt;
- every probe prints one compact JSON summary and saves the full response under
  ``backend/.cache/probes/`` (gitignored) so a paid call is never repeated just to
  look at it again.
"""

from __future__ import annotations

import base64
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

# Arabic output on a Windows console: force UTF-8 rather than crashing the summary
# after a paid call has already returned.
for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, "reconfigure"):
        stream.reconfigure(encoding="utf-8", errors="replace")

REPO_ROOT = Path(__file__).resolve().parents[2]
CACHE_DIR = REPO_ROOT / "backend" / ".cache" / "probes"


def load_env() -> None:
    """Read repo-root .env without a dependency; existing env vars win."""
    env_path = REPO_ROOT / ".env"
    if not env_path.is_file():
        return
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        name = name.strip()
        value = value.strip().strip('"').strip("'")
        if name and name not in os.environ:
            os.environ[name] = value


load_env()

BASE_URL = os.getenv("META_API_BASE_URL", "https://api.meta.ai/v1").rstrip("/")
SPARK_MODEL = os.getenv("MUSE_SPARK_MODEL", "muse-spark-1.3")
IMAGE_MODEL = os.getenv("MUSE_IMAGE_MODEL", "muse-image-1.0")
SAM_MODEL = os.getenv("SAM_MODEL", "sam-3.1")

# Published prices, https://dev.meta.ai/docs/pricing-rate-limits (checked 2026-10-27).
PRICE = {
    "spark_input_per_mtok": 1.25,
    "spark_output_per_mtok": 4.25,
    "image_per_image": 0.01,
    "sam_per_image": 2.50 / 1000,
}


def api_key() -> str:
    key = os.getenv("MODEL_API_KEY", "").strip()
    if not key:
        raise SystemExit(
            "MODEL_API_KEY is not set. Put it in L:\\naqsh\\.env (copy .env.example) "
            "or export it; this script never prompts for or prints a key."
        )
    return key


@dataclass
class CallResult:
    status: int
    latency_ms: int
    body: Any
    headers: dict[str, str]


def _maybe_json(raw: str) -> Any:
    """Parse a JSON body, keeping the text when the server answers in plain text."""
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return raw[:4000]


def post_json(path: str, payload: dict[str, Any], timeout: float = 120.0) -> CallResult:
    url = f"{BASE_URL}{path}"
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key()}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8", "replace")
            elapsed = int((time.perf_counter() - started) * 1000)
            return CallResult(response.status, elapsed, _maybe_json(raw), dict(response.headers))
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", "replace")
        elapsed = int((time.perf_counter() - started) * 1000)
        return CallResult(exc.code, elapsed, _maybe_json(raw), dict(exc.headers))


def stream_sse(path: str, payload: dict[str, Any], timeout: float = 180.0) -> Iterator[dict[str, Any]]:
    """Yield decoded SSE events from a Responses API stream."""
    body = dict(payload)
    body["stream"] = True
    request = urllib.request.Request(
        f"{BASE_URL}{path}",
        data=json.dumps(body).encode("utf-8"),
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key()}",
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            for raw_line in response:
                line = raw_line.decode("utf-8", "replace").strip()
                if not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if data == "[DONE]":
                    break
                try:
                    yield json.loads(data)
                except json.JSONDecodeError:
                    continue
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")
        raise SystemExit(f"HTTP {exc.code} from {path}: {detail[:800]}") from exc


def response_text(body: Any) -> str:
    """Extract assistant text from a Responses API body (shape varies by SDK/server)."""
    if not isinstance(body, dict):
        return ""
    if isinstance(body.get("output_text"), str) and body["output_text"]:
        return body["output_text"]
    chunks: list[str] = []
    for item in body.get("output", []) or []:
        for part in item.get("content", []) or []:
            if part.get("type") in ("output_text", "text") and isinstance(part.get("text"), str):
                chunks.append(part["text"])
    if chunks:
        return "".join(chunks)
    choices = body.get("choices") or []
    if choices:
        return choices[0].get("message", {}).get("content", "") or ""
    return ""


def data_url(image_path: str | Path) -> str:
    raw = Path(image_path).read_bytes()
    suffix = Path(image_path).suffix.lower()
    mime = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp"}.get(
        suffix, "image/png"
    )
    return f"data:{mime};base64,{base64.b64encode(raw).decode('ascii')}"


def receipt(name: str, payload: dict[str, Any]) -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = CACHE_DIR / f"{name}-{stamp}.json"
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def usage_of(body: Any) -> dict[str, Any]:
    if isinstance(body, dict) and isinstance(body.get("usage"), dict):
        return body["usage"]
    return {}


def spark_cost(usage: dict[str, Any]) -> float:
    prompt = usage.get("input_tokens") or usage.get("prompt_tokens") or 0
    completion = usage.get("output_tokens") or usage.get("completion_tokens") or 0
    return round(
        prompt / 1_000_000 * PRICE["spark_input_per_mtok"]
        + completion / 1_000_000 * PRICE["spark_output_per_mtok"],
        6,
    )


def summarize(name: str, *, model: str, result: CallResult, extra: dict[str, Any] | None = None) -> None:
    usage = usage_of(result.body)
    summary: dict[str, Any] = {
        "probe": name,
        "model": model,
        "http_status": result.status,
        "latency_ms": result.latency_ms,
        "usage": usage,
        "rate_limit_headers": {
            k: v for k, v in result.headers.items() if k.lower().startswith("x-ratelimit")
        },
    }
    if model == SPARK_MODEL:
        summary["cost_usd_estimate"] = spark_cost(usage)
    if extra:
        summary.update(extra)
    print(json.dumps(summary, indent=2, ensure_ascii=False))


# --- SAM payload helpers -------------------------------------------------------

BOX_RE = re.compile(r"<\|box;([^|]*)\|>")
MASK_RE = re.compile(r"<\|mask;([^|]*)\|>")
FRAME_RE = re.compile(r"^<(\d+)f>")


def parse_sam_line(line: str) -> dict[str, Any]:
    """Parse one SAM frame line into its boxes and raw mask descriptors."""
    frame_match = FRAME_RE.match(line)
    boxes = [dict(pair.split("=", 1) for pair in m.group(1).split(";") if "=" in pair) for m in BOX_RE.finditer(line)]
    masks = []
    for match in MASK_RE.finditer(line):
        raw = match.group(1)
        fields = dict(pair.split("=", 1) for pair in raw.split(";") if "=" in pair and not pair.startswith("data="))
        # "data=<H>,<W>,<enc><payload>"; the base85 payload may itself contain
        # commas, so split only twice and keep the remainder intact.
        data = raw.split("data=", 1)[1] if "data=" in raw else ""
        parts = data.split(",", 2)
        height, width, rest = (parts + ["", "", ""])[:3]
        enc = rest[:1]
        payload = rest[1:]
        masks.append(
            {
                "fields": fields,
                "height": int(height) if height.isdigit() else None,
                "width": int(width) if width.isdigit() else None,
                "encoding": enc,
                "payload_len": len(payload),
                "payload": payload,
            }
        )
    return {
        "frame": int(frame_match.group(1)) if frame_match else None,
        "boxes": boxes,
        "masks": masks,
        "raw_len": len(line),
    }
