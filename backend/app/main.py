"""Naqsh backend — FastAPI application.

The browser never talks to the model API: uploads, model calls, and pixels stay here.
"""

from __future__ import annotations

import io
import re
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from PIL import Image, UnidentifiedImageError
from starlette.concurrency import run_in_threadpool

from .config import settings
from .pipeline import job as job_module
from .pipeline.meta import MetaAPIError
from .pipeline.regions import REGISTERS

MAX_BYTES = 15 * 1024 * 1024
MAX_SIDE = 6000
SAFE_NAME = re.compile(r"^[a-z0-9][a-z0-9._-]*$")

app = FastAPI(
    title="Naqsh API",
    description="Arabic-first visual localizer — image to editable, localized layers.",
    version="0.2.0",
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
        "registers": sorted(REGISTERS),
        "models": {
            "spark": settings.spark_model,
            "image": settings.image_model,
            "sam": settings.sam_model,
        },
    }


@app.post("/api/localize")
async def localize(
    image: UploadFile = File(...),
    register_name: str = Form("egyptian", alias="register"),
) -> dict[str, object]:
    """Run the full pipeline on one uploaded page and return the receipt."""
    register = register_name
    if register not in REGISTERS:
        raise HTTPException(status_code=422, detail=f"register must be one of {sorted(REGISTERS)}")
    if not settings.has_key:
        raise HTTPException(status_code=503, detail="MODEL_API_KEY is not configured on the server")

    raw = await image.read()
    if not raw:
        raise HTTPException(status_code=422, detail="empty upload")
    if len(raw) > MAX_BYTES:
        raise HTTPException(status_code=413, detail="image larger than 15 MB")

    try:
        with Image.open(io.BytesIO(raw)) as probe:
            probe.verify()
        with Image.open(io.BytesIO(raw)) as probe:
            width, height = probe.size
    except UnidentifiedImageError as exc:
        raise HTTPException(status_code=422, detail="file is not a readable image") from exc
    if max(width, height) > MAX_SIDE:
        raise HTTPException(status_code=422, detail=f"image side longer than {MAX_SIDE}px")

    try:
        job = await run_in_threadpool(job_module.run_page_job, raw, register)
    except MetaAPIError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return job.to_dict()


@app.get("/api/jobs/{job_id}")
def get_job(job_id: str) -> dict[str, object]:
    if not SAFE_NAME.match(job_id):
        raise HTTPException(status_code=404, detail="job not found")
    job = job_module.load_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    return job


@app.get("/api/jobs/{job_id}/files/{name}")
def get_artifact(job_id: str, name: str) -> FileResponse:
    if not SAFE_NAME.match(job_id) or not SAFE_NAME.match(name) or "." not in name:
        raise HTTPException(status_code=404, detail="file not found")
    folder = (job_module.JOBS_DIR / job_id).resolve()
    path = (folder / name).resolve()
    if folder not in path.parents or not path.is_file():
        raise HTTPException(status_code=404, detail="file not found")
    return FileResponse(path)
