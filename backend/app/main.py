"""Naqsh backend — FastAPI application.

Phase 1 exposes only the health/version surface. The localization pipeline lands in
later phases; every endpoint stays a thin shell over testable modules.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings

app = FastAPI(
    title="Naqsh API",
    description="Arabic-first visual localizer — image to editable, localized layers.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
@app.get("/api/health")
def health() -> dict[str, object]:
    """Liveness plus a non-secret view of how the service is configured."""
    return {
        "status": "ok",
        "env": settings.env,
        "credential_configured": settings.has_key,
        "models": {
            "spark": settings.spark_model,
            "image": settings.image_model,
            "sam": settings.sam_model,
        },
    }
