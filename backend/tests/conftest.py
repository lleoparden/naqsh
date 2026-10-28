"""No test may reach the paid API unless it is explicitly marked ``live``.

Every test runs with demo mode on and no API key, so any accidental call to the model
client raises before an HTTP request is made. Mark a test ``@pytest.mark.live`` only
when a real call is the point of the test, and expect to pay for it.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Make `import app...` work whether pytest runs from the repo root or from backend/.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import settings  # noqa: E402


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "live: uses the paid model API on purpose")


@pytest.fixture(autouse=True)
def _offline_by_default(request: pytest.FixtureRequest):
    if request.node.get_closest_marker("live"):
        yield
        return
    previous_demo = settings.demo_mode
    previous_key = settings.api_key
    object.__setattr__(settings, "demo_mode", True)
    object.__setattr__(settings, "api_key", "")
    try:
        yield
    finally:
        object.__setattr__(settings, "demo_mode", previous_demo)
        object.__setattr__(settings, "api_key", previous_key)
