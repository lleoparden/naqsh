"""Naqsh backend — configuration.

Secrets come from the environment or the repository-root ``.env``. They are never
logged, echoed, or returned by an endpoint.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_env() -> None:
    """Load the repo-root .env once, without overriding real environment values."""
    for candidate in (REPO_ROOT / ".env", Path.cwd() / ".env"):
        if candidate.is_file():
            load_dotenv(candidate, override=False)
            return


_load_env()


@dataclass(frozen=True)
class Settings:
    api_key: str = field(default_factory=lambda: os.getenv("MODEL_API_KEY", ""))
    base_url: str = field(
        default_factory=lambda: os.getenv("META_API_BASE_URL", "https://api.meta.ai/v1").rstrip("/")
    )
    spark_model: str = field(
        default_factory=lambda: os.getenv("MUSE_SPARK_MODEL", "muse-spark-1.3")
    )
    image_model: str = field(
        default_factory=lambda: os.getenv("MUSE_IMAGE_MODEL", "muse-image-1.0")
    )
    sam_model: str = field(default_factory=lambda: os.getenv("SAM_MODEL", "sam-3.1"))
    env: str = field(default_factory=lambda: os.getenv("NAQSH_ENV", "development"))
    # Replay recorded runs for known demo fixtures instead of calling the model API.
    demo_mode: bool = field(
        default_factory=lambda: os.getenv("DEMO_MODE", "").strip().lower() not in ("", "0", "false", "no")
    )
    cors_origins: list[str] = field(
        default_factory=lambda: [
            o.strip()
            for o in os.getenv("NAQSH_CORS_ORIGINS", "http://localhost:5173").split(",")
            if o.strip()
        ]
    )

    @property
    def has_key(self) -> bool:
        return bool(self.api_key)


settings = Settings()
