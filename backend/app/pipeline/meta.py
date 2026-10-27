"""Thin, testable client for the Meta Model API.

Every paid call goes through here so cost and usage are accounted in one place.
The API key is read from settings, sent only in the Authorization header, and never
logged or returned in an error message.
"""

from __future__ import annotations

import asyncio
import base64
import json
import time
from dataclasses import dataclass, field
from typing import Any

import requests

from ..config import settings

# Published prices, https://dev.meta.ai/docs/pricing-rate-limits (2026-10-27).
SPARK_INPUT_PER_MTOK = 1.25
SPARK_OUTPUT_PER_MTOK = 4.25
IMAGE_PER_IMAGE = 0.01
SAM_PER_IMAGE = 2.50 / 1000


class MetaAPIError(RuntimeError):
    """A model call failed. Carries the status and a safe slice of the body."""

    def __init__(self, status: int, message: str, body: str = "") -> None:
        super().__init__(f"Meta API {status}: {message}")
        self.status = status
        self.body = body[:2000]


@dataclass
class Usage:
    input_tokens: int = 0
    output_tokens: int = 0
    reasoning_tokens: int = 0
    images: int = 0

    @classmethod
    def from_response(cls, payload: dict[str, Any]) -> "Usage":
        raw = payload.get("usage") or {}
        details = raw.get("output_tokens_details") or {}
        return cls(
            input_tokens=int(raw.get("input_tokens") or 0),
            output_tokens=int(raw.get("output_tokens") or 0),
            reasoning_tokens=int(details.get("reasoning_tokens") or 0),
            images=int(raw.get("images_processed") or 0),
        )

    def spark_cost(self) -> float:
        return (
            self.input_tokens / 1_000_000 * SPARK_INPUT_PER_MTOK
            + self.output_tokens / 1_000_000 * SPARK_OUTPUT_PER_MTOK
        )

    def to_dict(self) -> dict[str, int]:
        return {
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "reasoning_tokens": self.reasoning_tokens,
            "images": self.images,
        }


def _headers() -> dict[str, str]:
    if not settings.api_key:
        raise MetaAPIError(0, "MODEL_API_KEY is not configured")
    return {
        "Authorization": f"Bearer {settings.api_key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def _post(path: str, payload: dict[str, Any], timeout: float = 180.0, attempts: int = 2) -> dict[str, Any]:
    """POST a JSON body, retrying transient failures with backoff.

    Timeouts are (connect, read) tuples so a stalled response cannot hang a job
    indefinitely: no single read may take longer than the read timeout.
    """
    url = f"{settings.base_url}{path}"
    connect_timeout = 10.0
    read_timeout = max(30.0, min(timeout, 150.0))
    last_error: MetaAPIError | None = None
    for attempt in range(attempts):
        try:
            response = requests.post(
                url, headers=_headers(), json=payload, timeout=(connect_timeout, read_timeout)
            )
        except requests.Timeout as exc:
            last_error = MetaAPIError(0, f"timeout after {read_timeout:.0f}s")
            time.sleep(1.5 * (attempt + 1))
            continue
        except requests.RequestException as exc:
            last_error = MetaAPIError(0, f"transport error: {type(exc).__name__}")
            time.sleep(1.5 * (attempt + 1))
            continue
        if response.status_code < 400:
            try:
                return response.json()
            except ValueError as exc:
                raise MetaAPIError(response.status_code, "response was not JSON") from exc
        try:
            body = response.json()
            message = (body.get("error") or {}).get("message") or response.text[:300]
        except ValueError:
            message = response.text[:300]
        last_error = MetaAPIError(response.status_code, message)
        if response.status_code in (429, 500, 502, 503, 504) and attempt + 1 < attempts:
            retry_after = float(response.headers.get("Retry-After") or 0)
            time.sleep(max(retry_after, 1.5 * (attempt + 1)))
            continue
        raise last_error
    raise last_error or MetaAPIError(0, "request failed")


def _post_stream(path: str, payload: dict[str, Any], timeout: float = 240.0) -> tuple[list[dict[str, Any]], str]:
    """POST and collect an SSE stream. Returns (events, concatenated text deltas)."""
    body = dict(payload)
    body["stream"] = True
    headers = _headers()
    headers["Accept"] = "text/event-stream"
    events: list[dict[str, Any]] = []
    text_parts: list[str] = []
    with requests.post(f"{settings.base_url}{path}", headers=headers, json=body, stream=True, timeout=timeout) as response:
        if response.status_code >= 400:
            detail = response.text[:800]
            raise MetaAPIError(response.status_code, detail)
        for raw in response.iter_lines(decode_unicode=True):
            if not raw or not raw.startswith("data:"):
                continue
            data = raw[5:].strip()
            if data == "[DONE]":
                break
            try:
                event = json.loads(data)
            except json.JSONDecodeError:
                continue
            events.append(event)
            if event.get("type") == "response.output_text.delta":
                text_parts.append(event.get("delta", ""))
    return events, "".join(text_parts)


def _data_url(png: bytes) -> str:
    return "data:image/png;base64," + base64.b64encode(png).decode("ascii")


def spark_json(image_png: bytes, prompt: str, *, max_output_tokens: int = 2600) -> tuple[dict[str, Any], Usage, str]:
    """Send an image + instruction to Muse Spark and parse a JSON object reply."""
    payload = {
        "model": settings.spark_model,
        "input": [
            {
                "type": "message",
                "role": "user",
                "content": [
                    {"type": "input_text", "text": prompt},
                    {"type": "input_image", "image_url": _data_url(image_png)},
                ],
            }
        ],
        "reasoning": {"effort": "minimal"},
        "max_output_tokens": max_output_tokens,
    }
    started = time.perf_counter()
    body = _post("/responses", payload)
    if body.get("status") == "incomplete":
        raise MetaAPIError(200, f"response incomplete: {body.get('incomplete_details')}")
    text = _response_text(body)
    _ = time.perf_counter() - started
    return _parse_json_object(text), Usage.from_response(body), text


def _response_text(body: dict[str, Any]) -> str:
    if isinstance(body.get("output_text"), str) and body["output_text"]:
        return body["output_text"]
    parts: list[str] = []
    for item in body.get("output") or []:
        for part in item.get("content") or []:
            if part.get("type") in ("output_text", "text") and isinstance(part.get("text"), str):
                parts.append(part["text"])
    return "".join(parts)


def _parse_json_object(text: str) -> dict[str, Any]:
    try:
        value = json.loads(text)
        return value if isinstance(value, dict) else {}
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if 0 <= start < end:
            try:
                value = json.loads(text[start : end + 1])
                return value if isinstance(value, dict) else {}
            except json.JSONDecodeError:
                pass
    raise MetaAPIError(200, "model reply was not JSON")


@dataclass
class SamObject:
    object_id: str
    box: tuple[int, int, int, int, int, int]  # x1, y1, x2, y2, frame_w, frame_h
    confidence: float
    width: int
    height: int
    raster: bytes  # 0/1 per pixel, row-major
    usage: Usage = field(default_factory=Usage)


def sam_segment(
    image_png: bytes, prompt_text: str, *, image_size: tuple[int, int], timeout: float = 240.0
) -> tuple[list[SamObject], Usage]:
    """Segment with SAM 3.1. ``prompt_text`` is a concept or a box-prompt string."""
    payload = {
        "model": settings.sam_model,
        "input": [
            {
                "type": "message",
                "role": "user",
                "content": [
                    {"type": "input_text", "text": prompt_text},
                    {"type": "input_image", "image_url": _data_url(image_png)},
                ],
            }
        ],
        "metadata": {"mask_encoding": "one_bit", "include_confidence": "true"},
    }
    events, _text = _post_stream("/responses", payload, timeout=timeout)
    usage = Usage(images=1)
    for event in events:
        if event.get("type") == "response.completed":
            usage = Usage.from_response((event.get("response") or {}))
    return _decode_sam(events, image_size), usage


def _decode_sam(events: list[dict[str, Any]], image_size: tuple[int, int]) -> list[SamObject]:
    import meta_sam_parser as msp

    async def run() -> Any:
        async def gen():
            for event in events:
                yield event

        parsed = msp.parse_responses_stream(gen(), msp.image_segmentation_format())
        return await parsed.final_result()

    result = asyncio.run(run())
    frame_w, frame_h = image_size
    objects: list[SamObject] = []
    for record in result.records:
        if getattr(record, "kind", None) != "mask":
            continue
        bounds = record.bounds
        if bounds is None:
            continue
        objects.append(
            SamObject(
                object_id=str(record.object_id),
                box=(
                    int(round(bounds.left)),
                    int(round(bounds.top)),
                    int(round(bounds.right)),
                    int(round(bounds.bottom)),
                    frame_w,
                    frame_h,
                ),
                confidence=float(record.confidence or 0.0),
                width=int(record.mask.width),
                height=int(record.mask.height),
                raster=msp.decode_mask_to_raster(record.mask),
            )
        )
    return objects


def image_generate(prompt: str, *, size: str = "1024x1536", timeout: float = 300.0) -> tuple[bytes, Usage]:
    """Text-to-image; returns PNG bytes (used for fixtures and the demo test page)."""
    payload = {
        "model": settings.image_model,
        "prompt": prompt,
        "n": 1,
        "size": size,
        "output_format": "png",
        "response_format": "b64_json",
    }
    body = _post("/images/generations", payload, timeout=timeout)
    data = body.get("data") or []
    if not data or not data[0].get("b64_json"):
        raise MetaAPIError(200, "generation returned no image")
    return base64.b64decode(data[0]["b64_json"]), Usage(images=1)


def image_edit(image_png: bytes, prompt: str, *, timeout: float = 300.0) -> tuple[bytes, Usage]:
    """Instruction-based edit; returns PNG bytes."""
    payload = {
        "model": settings.image_model,
        "prompt": prompt,
        "images": [{"image_url": _data_url(image_png)}],
        "n": 1,
        "output_format": "png",
        "response_format": "b64_json",
    }
    body = _post("/images/edits", payload, timeout=timeout)
    data = body.get("data") or []
    if not data or not data[0].get("b64_json"):
        raise MetaAPIError(200, "edit returned no image")
    return base64.b64decode(data[0]["b64_json"]), Usage.from_response(body)
