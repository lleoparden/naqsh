"""Server-side guards for expensive per-region actions.

Re-translate costs credits, so a double-click or a stuck UI must not be able to bill
twice: one in-flight call per region, and a small per-job budget per minute. The UI
disables the button too, but the server is the authority.
"""

from __future__ import annotations

import threading
import time

_PER_JOB_LIMIT = 6
_WINDOW_SECONDS = 60.0

_lock = threading.Lock()
_in_flight: set[tuple[str, str]] = set()
_hits: dict[str, list[float]] = {}


def acquire(job_id: str, layer_id: str) -> str | None:
    """Reserve one re-translate. Returns None on success, else 'in_flight'/'rate_limited'."""
    now = time.monotonic()
    key = (job_id, layer_id)
    with _lock:
        if key in _in_flight:
            return "in_flight"
        recent = [stamp for stamp in _hits.get(job_id, []) if now - stamp < _WINDOW_SECONDS]
        if len(recent) >= _PER_JOB_LIMIT:
            _hits[job_id] = recent
            return "rate_limited"
        recent.append(now)
        _hits[job_id] = recent
        _in_flight.add(key)
        return None


def release(job_id: str, layer_id: str) -> None:
    with _lock:
        _in_flight.discard((job_id, layer_id))


def reset() -> None:
    """Test helper: forget all locks and counters."""
    with _lock:
        _in_flight.clear()
        _hits.clear()
