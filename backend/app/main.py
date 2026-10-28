"""Naqsh backend — FastAPI application.

The browser never talks to the model API: uploads, model calls, and pixels stay here.
"""

from __future__ import annotations

import io
import re
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from PIL import Image, UnidentifiedImageError
from starlette.concurrency import run_in_threadpool

from .config import settings
from .pipeline import demo as demo_module
from .pipeline import document as document_module
from .pipeline import export as export_module
from .pipeline import job as job_module
from .pipeline import spend
from .pipeline import throttle
from .pipeline.meta import MetaAPIError, spark_translate
from .pipeline.regions import REGISTERS

MAX_BYTES = 15 * 1024 * 1024
MAX_SIDE = 6000
SAFE_NAME = re.compile(r"^[a-z0-9][a-z0-9._-]*$")
REPO_ROOT = Path(__file__).resolve().parents[2]

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

    # Demo mode: a byte-for-byte known fixture replays its recorded run, timings and
    # cost untouched, and needs no API key. Anything else falls through to live.
    if settings.demo_mode:
        entry = demo_module.find(raw)
        if entry is not None:
            receipt = await run_in_threadpool(demo_module.materialise, entry)
            if receipt is not None:
                return receipt

    if not settings.has_key:
        raise HTTPException(status_code=503, detail="MODEL_API_KEY is not configured on the server")

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


def _document(job_id: str):
    if not SAFE_NAME.match(job_id):
        raise HTTPException(status_code=404, detail="job not found")
    receipt = job_module.load_job(job_id)
    if receipt is None:
        raise HTTPException(status_code=404, detail="job not found")
    folder = job_module.JOBS_DIR / job_id
    return folder, document_module.load_document(folder, receipt)


@app.get("/api/jobs/{job_id}/document")
def get_document(job_id: str) -> dict[str, object]:
    _folder, doc = _document(job_id)
    return doc.to_dict()


@app.patch("/api/jobs/{job_id}/document")
def patch_document(job_id: str, body: dict[str, object]) -> dict[str, object]:
    folder, doc = _document(job_id)
    if "register" in body and str(body["register"]) in ("egyptian", "msa"):
        doc.register = str(body["register"])
    if "numerals" in body and str(body["numerals"]) in ("latin", "arabic-indic"):
        doc.numerals = str(body["numerals"])
    touched: set[str] = set()
    for update in body.get("layers") or []:  # type: ignore[union-attr]
        if not isinstance(update, dict):
            continue
        layer = doc.layer(str(update.get("id")))
        if layer is None:
            continue
        if "action" in update:
            layer.action = str(update["action"])
        if "box" in update and isinstance(update["box"], list) and len(update["box"]) == 4:
            layer.box = [int(v) for v in update["box"]]  # type: ignore[arg-type]
        if "font_family" in update:
            layer.font_family = str(update["font_family"])
        if "font_size" in update:
            layer.font_size = min(1000, max(0, int(update["font_size"])))  # type: ignore[arg-type]
        if "color" in update and isinstance(update["color"], list):
            layer.color = [int(v) for v in update["color"]]  # type: ignore[arg-type]
        if "visible" in update:
            layer.visible = bool(update["visible"])
        if "locked" in update:
            layer.locked = bool(update["locked"])
        if "z" in update:
            layer.z = int(update["z"])  # type: ignore[arg-type]
        if "arabic" in update and isinstance(update["arabic"], dict):
            for register_name, value in update["arabic"].items():  # type: ignore[union-attr]
                if register_name in ("egyptian", "msa"):
                    layer.arabic[register_name] = str(value)
        if isinstance(update.get("fill"), list):
            layer.fill = [int(v) for v in update["fill"]]  # type: ignore[arg-type]
        if "name" in update:
            layer.name = str(update["name"])[:80]
        if "shape" in update and str(update["shape"]) in ("rect", "ellipse"):
            layer.shape = str(update["shape"])
        touched.add(layer.id)
    document_module.layout_document(doc, only_layer=None)
    document_module.save_document(folder, doc)
    return doc.to_dict()


@app.post("/api/jobs/{job_id}/reset-region")
def reset_region(job_id: str, body: dict[str, object]) -> dict[str, object]:
    """Restore one region to its first AI result (text, font, size, colour, box, action)."""
    folder, doc = _document(job_id)
    layer = doc.layer(str(body.get("layer_id") or ""))
    if layer is None or layer.kind != "text":
        raise HTTPException(status_code=404, detail="text layer not found")
    original = layer.original
    if not original:
        raise HTTPException(status_code=409, detail="this layer has no saved AI result")
    if isinstance(original.get("arabic"), dict):
        layer.arabic = {str(k): str(v) for k, v in original["arabic"].items()}
    if "font_family" in original:
        layer.font_family = str(original["font_family"])
    if "color" in original and isinstance(original["color"], list):
        layer.color = [int(v) for v in original["color"]]
    if "box" in original and isinstance(original["box"], list) and len(original["box"]) == 4:
        layer.box = [int(v) for v in original["box"]]
    if "action" in original:
        layer.action = str(original["action"])
    text = layer.active_text(doc.register)
    size, lines = document_module.layout_text(
        text,
        layer.box,
        family=layer.font_family,
        register=doc.register,
        numerals=doc.numerals,
        action=layer.action,
        size_limit=int(original.get("font_size") or 0) or None,
    )
    layer.font_size = size
    layer.lines = lines
    document_module.save_document(folder, doc)
    return {"layer": layer.to_dict(), "size": size}


@app.post("/api/jobs/{job_id}/layout")
def layout_region(job_id: str, body: dict[str, object]) -> dict[str, object]:
    folder, doc = _document(job_id)
    layer = doc.layer(str(body.get("layer_id") or ""))
    if layer is None:
        raise HTTPException(status_code=404, detail="layer not found")
    if "text" in body:
        layer.arabic[doc.register] = str(body["text"])
    if "box" in body and isinstance(body["box"], list) and len(body["box"]) == 4:
        layer.box = [int(v) for v in body["box"]]  # type: ignore[arg-type]
    if "font_family" in body:
        layer.font_family = str(body["font_family"])
    if "font_size" in body:
        layer.font_size = min(1000, max(0, int(body["font_size"])))  # type: ignore[arg-type]
    text = layer.active_text(doc.register)
    size, lines = document_module.layout_text(
        text,
        layer.box,
        family=layer.font_family,
        register=doc.register,
        numerals=doc.numerals,
        action=layer.action,
        size_limit=layer.font_size or None,
    )
    layer.font_size = size
    layer.lines = lines
    document_module.save_document(folder, doc)
    return {"layer": layer.to_dict(), "size": size}


@app.post("/api/jobs/{job_id}/retranslate")
def retranslate_region(job_id: str, body: dict[str, object]) -> dict[str, object]:
    folder, doc = _document(job_id)
    layer = doc.layer(str(body.get("layer_id") or ""))
    if layer is None:
        raise HTTPException(status_code=404, detail="layer not found")
    register_name = str(body.get("register") or doc.register)
    if register_name not in ("egyptian", "msa"):
        raise HTTPException(status_code=422, detail="register must be egyptian or msa")
    if settings.demo_mode:
        cached = demo_module.replay_retranslate(doc, layer.id, register_name)
        if cached:
            layer.arabic[register_name] = cached
            size, lines = document_module.layout_text(
                cached,
                layer.box,
                family=layer.font_family,
                register=register_name,
                numerals=doc.numerals,
                action=layer.action,
                size_limit=layer.font_size or None,
            )
            layer.font_size = size
            layer.lines = lines
            document_module.save_document(folder, doc)
            return {
                "layer": layer.to_dict(),
                "cost_usd": 0.0,
                "demo": True,
                "note": "replayed from the recorded run; no model call",
            }
    if not settings.has_key:
        raise HTTPException(status_code=503, detail="MODEL_API_KEY is not configured on the server")
    refusal = throttle.acquire(job_id, layer.id)
    if refusal == "in_flight":
        raise HTTPException(status_code=429, detail="this region is already being re-translated")
    if refusal == "rate_limited":
        raise HTTPException(status_code=429, detail="too many re-translations for this job; wait a minute")
    try:
        text, usage = spark_translate(
            layer.source_text,
            layer.active_text(register_name),
            str(body.get("note") or "re-translate for this register"),
            REGISTERS[register_name],
        )
    except MetaAPIError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    finally:
        throttle.release(job_id, layer.id)
    cost = usage.spark_cost()
    spend.record_spend(f"retranslate {job_id}/{layer.id}", cost, kind="text")
    layer.arabic[register_name] = text
    size, lines = document_module.layout_text(
        text,
        layer.box,
        family=layer.font_family,
        register=register_name,
        numerals=doc.numerals,
        action=layer.action,
        size_limit=layer.font_size or None,
    )
    layer.font_size = size
    layer.lines = lines
    document_module.save_document(folder, doc)
    return {"layer": layer.to_dict(), "cost_usd": round(cost, 6), "usage": usage.to_dict()}


@app.get("/api/jobs/{job_id}/export.svg")
def export_svg(job_id: str) -> Response:
    folder, doc = _document(job_id)
    return Response(
        content=export_module.build_svg(doc, folder, outlined=False),
        media_type="image/svg+xml",
        headers={"Content-Disposition": f'inline; filename="naqsh-{job_id}.svg"'},
    )


@app.get("/api/jobs/{job_id}/export-outlined.svg")
def export_svg_outlined(job_id: str) -> Response:
    folder, doc = _document(job_id)
    return Response(
        content=export_module.build_svg(doc, folder, outlined=True),
        media_type="image/svg+xml",
        headers={"Content-Disposition": f'inline; filename="naqsh-{job_id}-outlined.svg"'},
    )


@app.get("/api/jobs/{job_id}/export.png")
def export_png(job_id: str) -> Response:
    folder, doc = _document(job_id)
    image = export_module.render_png(doc, folder)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return Response(
        content=buffer.getvalue(),
        media_type="image/png",
        headers={"Content-Disposition": f'attachment; filename="naqsh-{job_id}.png"'},
    )


@app.get("/api/jobs/{job_id}/export.zip")
def export_zip(job_id: str) -> Response:
    folder, doc = _document(job_id)
    return Response(
        content=export_module.build_bundle(doc, folder),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="naqsh-{job_id}.zip"'},
    )


@app.get("/api/fonts/{name}")
def get_font(name: str) -> FileResponse:
    allowed = {info[2] for info in export_module.FONT_NAMES.values()} | set(export_module.LICENSES.values())
    # Bundled UI fonts (docs/ui-design-brief.md).
    allowed |= {
        "Inter-Variable.ttf",
        "IBMPlexSansArabic-Regular.ttf",
        "IBMPlexSansArabic-SemiBold.ttf",
        "OFL-Inter.txt",
        "OFL-IBMPlexSansArabic.txt",
    }
    if name not in allowed:
        raise HTTPException(status_code=404, detail="font not found")
    path = (REPO_ROOT / "assets" / "fonts" / name).resolve()
    if not path.is_file():
        raise HTTPException(status_code=404, detail="font not found")
    return FileResponse(path, media_type="font/ttf", headers={"Cache-Control": "public, max-age=86400"})


@app.post("/api/jobs/{job_id}/cover")
def add_cover(job_id: str, body: dict[str, object]) -> dict[str, object]:
    folder, doc = _document(job_id)
    box = body.get("box")
    if not isinstance(box, list) or len(box) != 4:
        raise HTTPException(status_code=422, detail="box must be [x1,y1,x2,y2]")
    fill = body.get("fill")
    if not isinstance(fill, list) or len(fill) != 3:
        fill = [246, 240, 226]
    cover = document_module.Layer(
        id=f"cover-{len([layer for layer in doc.layers if layer.kind == 'cover']) + 1}",
        kind="cover",
        box=[int(v) for v in box],  # type: ignore[arg-type]
        type="cover",
        action="keep",
        fill=[int(v) for v in fill],  # type: ignore[arg-type]
        shape=str(body.get("shape") or "rect") if str(body.get("shape") or "rect") in ("rect", "ellipse") else "rect",
        z=len(doc.layers),
    )
    doc.layers.append(cover)
    document_module.save_document(folder, doc)
    return doc.to_dict()
