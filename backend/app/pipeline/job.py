"""Job orchestration: one page in, artifacts and a cost/timing receipt out.

Each stage reports its own wall time and cost, so the receipt is evidence rather
than an estimate. Artifacts are written under ``backend/.cache/jobs/<id>/`` and
served by the API; the repo only keeps the evidence chosen for docs/.

Clean-plate routing (Phase 4):
    Muse Image plate -> registered + masked composite -> Spark residual check
    -> one plate retry if any region still shows lettering
    -> flat interior fill for flat regions / Telea inpaint for textured ones.
Every region records which strategy produced its final pixels.
"""

from __future__ import annotations

import io
import json
import time
import uuid
from pathlib import Path

from PIL import Image

from . import coverage as coverage_stage
from . import plate as plate_stage
from . import regions as regions_stage
from . import render as render_stage
from . import residual as residual_stage
from . import segment as segment_stage
from . import typeset
from .meta import MetaAPIError
from .types import BBox, Layout, PageJob

REPO_ROOT = Path(__file__).resolve().parents[3]
JOBS_DIR = REPO_ROOT / "backend" / ".cache" / "jobs"


def _ms(started: float) -> int:
    return int(round((time.perf_counter() - started) * 1000))


def family_for(font_style: str) -> str:
    """A crude style map for Phase 2; Phase 3 replaces it with a real matcher."""
    text = font_style.lower()
    if any(word in text for word in ("naskh", "serif", "calligraph", "script", "brush")):
        return "naskh"
    return "kufi"


def _container_for(reading_box: BBox, mask: Image.Image) -> BBox:
    """The area text may fill: the bubble/panel the lettering sits in.

    The mask is eroded first so the inscribed area is used rather than the full
    bounding box (a bubble's box includes its tail and widest points). The result is
    intersected with the reading box plus a margin so text cannot drift into a tail.
    A mask much smaller than the reading box means SAM found only part of the
    lettering, so the reading box is used instead.
    """
    bounds = mask.getbbox()
    if not bounds:
        return reading_box
    candidate = BBox(*bounds)
    if candidate.width * candidate.height < 0.6 * reading_box.width * reading_box.height:
        return reading_box

    interior = segment_stage.inner_box(mask) or candidate
    slack_x = int(reading_box.width * 0.25)
    slack_y = int(reading_box.height * 0.25)
    allowed = BBox(
        reading_box.x1 - slack_x,
        reading_box.y1 - slack_y,
        reading_box.x2 + slack_x,
        reading_box.y2 + slack_y,
    )
    x1, y1 = max(interior.x1, allowed.x1), max(interior.y1, allowed.y1)
    x2, y2 = min(interior.x2, allowed.x2), min(interior.y2, allowed.y2)
    if x2 - x1 < 24 or y2 - y1 < 24:
        return reading_box
    return BBox(x1, y1, x2, y2)


def _compose(
    source: Image.Image,
    aligned: Image.Image,
    coverage: dict[str, Image.Image],
    masks: dict[str, Image.Image],
) -> tuple[Image.Image, dict[str, float], int]:
    composite, stats = plate_stage.composite(source, aligned, list(coverage.values()))
    cleaned = 0
    for mask in masks.values():
        composite, changed = segment_stage.clean_flat_interior(composite, mask)
        cleaned += int(changed)
    return composite, stats, cleaned


def _check(composite: Image.Image, regions: list) -> tuple[list, float, dict]:
    """One Spark vision call over every region crop; returns verdicts and cost."""
    boxes = {region.id: region.bbox for region in regions}
    verdicts, usage, _raw = residual_stage.detect_residual(composite, boxes)
    return verdicts, usage.spark_cost(), residual_stage.summarise(verdicts)


def run_page_job(image_bytes: bytes, register: str = "egyptian") -> PageJob:
    job_id = uuid.uuid4().hex[:12]
    folder = JOBS_DIR / job_id
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "source.png").write_bytes(image_bytes)

    with Image.open(io.BytesIO(image_bytes)) as opened:
        source = opened.convert("RGB")
    width, height = source.size
    job = PageJob(id=job_id, register=register, width=width, height=height)
    job.artifacts["source"] = "source.png"

    # 1. Read + translate ---------------------------------------------------------
    started = time.perf_counter()
    regions, usage = regions_stage.read_regions(image_bytes, width, height, register)
    job.regions = regions
    job.add_stage("read", _ms(started), usage.spark_cost(), **usage.to_dict(), regions=len(regions))
    if not regions:
        job.warnings.append("no text regions found")
        _finish(job, folder, source, source)
        return job

    # 2. Segment + ink-derived coverage --------------------------------------------
    started = time.perf_counter()
    masks, sam_usage, warnings = segment_stage.segment_regions(image_bytes, regions, width, height)
    job.warnings.extend(warnings)
    coverage: dict[str, Image.Image] = {}
    for region in regions:
        mask = masks.get(region.id)
        if mask is None:
            continue
        region.container = _container_for(region.bbox, mask)
        coverage[region.id], _area = coverage_stage.coverage_for(source, mask, region.bbox)
        name = f"mask-{region.id}.png"
        mask.save(folder / name)
        region.mask_path = name
    job.add_stage(
        "segment",
        _ms(started),
        sam_usage.images * 2.50 / 1000,
        masks=len(masks),
        concepts="box prompts + ink extent",
    )
    overlay = segment_stage.overlay_preview(source, coverage)
    overlay.save(folder / "masks-overlay.png")
    job.artifacts["mask_overlay"] = "masks-overlay.png"

    # 3. Clean plate --------------------------------------------------------------
    started = time.perf_counter()
    plate_raw, _plate_usage = plate_stage.clean_plate(image_bytes)
    with Image.open(io.BytesIO(plate_raw)) as opened:
        plate_image = opened.convert("RGB")
    plate_size = plate_image.size
    (folder / "plate-raw.png").write_bytes(plate_raw)
    job.artifacts["plate_raw"] = "plate-raw.png"
    job.add_stage(
        "clean_plate",
        _ms(started),
        0.01,
        images=1,
        plate_size=list(plate_size),
    )

    # 4. Register + composite ------------------------------------------------------
    started = time.perf_counter()
    dx, dy = plate_stage.estimate_shift(source, plate_image, [r.bbox for r in regions])
    aligned = plate_stage.apply_shift(plate_image, (width, height), dx, dy)
    aligned.save(folder / "plate.png")
    job.artifacts["plate"] = "plate.png"
    composite, stats, flat_cleaned = _compose(source, aligned, coverage, masks)
    alignment = plate_stage.alignment_report(source, aligned, list(coverage.values()))
    composite.save(folder / "composite.png")
    job.artifacts["composite"] = "composite.png"
    job.add_stage(
        "register_composite",
        _ms(started),
        0.0,
        shift=[dx, dy],
        vertical_only=dx == 0,
        scale_ratio=[round(width / plate_size[0], 4), round(height / plate_size[1], 4)],
        flat_interiors_cleaned=flat_cleaned,
        # This is a sanity check and tautological by construction: the composite copies
        # original pixels outside the mask, so it must be 0 unless the code is broken.
        outside_untouched_mean_diff_is_tautological=stats["outside_untouched_mean_diff"],
        **alignment,
    )

    # 5. Verify with the model, route what still fails -----------------------------
    started = time.perf_counter()
    strategies: dict[str, str] = {region.id: "muse" for region in regions}
    verify_cost = 0.0
    try:
        verdicts, cost, summary = _check(composite, regions)
        verify_cost += cost
        remaining = [v.region_id for v in verdicts if v.residual]
        notes = summary["notes"]
        job.add_stage("verify", _ms(started), verify_cost, **summary)

        if remaining:
            retry_started = time.perf_counter()
            retry_raw, _ = plate_stage.clean_plate(image_bytes, retry=True)
            with Image.open(io.BytesIO(retry_raw)) as opened:
                retry_image = opened.convert("RGB")
            retry_dx, retry_dy = plate_stage.estimate_shift(source, retry_image, [r.bbox for r in regions])
            retry_aligned = plate_stage.apply_shift(retry_image, (width, height), retry_dx, retry_dy)
            retry_composite, retry_stats, retry_flat = _compose(source, retry_aligned, coverage, masks)
            verdicts2, cost2, summary2 = _check(retry_composite, regions)
            still = [v.region_id for v in verdicts2 if v.residual]
            # Keep whichever plate leaves fewer regions with residual text.
            if len(still) <= len(remaining):
                composite, aligned, stats = retry_composite, retry_aligned, retry_stats
                remaining = still
                notes = summary2["notes"]
                for region_id in strategies:
                    strategies[region_id] = "muse-retry"
                retry_aligned.save(folder / "plate.png")
                composite.save(folder / "composite.png")
            job.add_stage(
                "retry",
                _ms(retry_started),
                0.01 + cost2,
                retried=", ".join(sorted(set(v.region_id for v in verdicts if v.residual))) or "none",
                still_residual=remaining,
                notes=notes,
                shift=[retry_dx, retry_dy],
            )

            if remaining:
                repair_started = time.perf_counter()
                for region in regions:
                    if region.id not in remaining:
                        continue
                    mask = masks.get(region.id)
                    cov = coverage.get(region.id)
                    if mask is None or cov is None:
                        continue
                    if residual_stage.region_is_flat(composite, mask):
                        composite, changed = residual_stage.flat_fill(composite, mask, cov)
                        strategies[region.id] = "flat-fill" if changed else "muse"
                        if not changed:
                            job.warnings.append(f"{region.id}: flat fill skipped (not flat)")
                    else:
                        composite = residual_stage.inpaint_region(composite, cov)
                        strategies[region.id] = "inpaint"
                composite.save(folder / "composite.png")
                job.add_stage(
                    "repair",
                    _ms(repair_started),
                    0.0,
                    strategies={k: v for k, v in strategies.items() if v in ("flat-fill", "inpaint")},
                )

        # Final independent check on what the composite actually looks like now.
        final_started = time.perf_counter()
        final_verdicts, final_cost, final_summary = _check(composite, regions)
        job.add_stage("final_check", _ms(final_started), final_cost, **final_summary)
    except MetaAPIError as exc:
        job.warnings.append(f"residual check unavailable: {exc}")

    for region in regions:
        region.strategy = strategies.get(region.id, "muse")

    # 6. Typeset + render ---------------------------------------------------------
    started = time.perf_counter()
    layouts: dict[str, Layout] = {}
    colors: dict[str, tuple[int, int, int]] = {}
    for region in regions:
        region.font_family = family_for(region.font_style)
        container = region.container or region.bbox
        layout = typeset.fit_text(
            region.translation_ar,
            container.width,
            container.height,
            family=region.font_family,
            padding=6,
        )
        region.font_size = layout.size
        region.lines = layout.lines
        layouts[region.id] = layout
        colors[region.id] = render_stage.contrast_color(source, region)
        if layout.overflow:
            job.warnings.append(f"{region.id}: text did not fit and was clamped")
    final = render_stage.draw_regions(composite, regions, layouts, color_of=colors)
    final.save(folder / "output.png")
    job.artifacts["output"] = "output.png"
    job.add_stage("typeset", _ms(started), 0.0, regions=len(layouts), strategies=strategies)

    _finish(job, folder, source, final)
    return job


def _finish(job: PageJob, folder: Path, source: Image.Image, final: Image.Image) -> None:
    """Write the side-by-side evidence image and the job receipt."""
    combo = Image.new("RGB", (source.width * 2 + 24, source.height), "white")
    combo.paste(source, (0, 0))
    combo.paste(final, (source.width + 24, 0))
    combo.save(folder / "before-after.png")
    job.artifacts["before_after"] = "before-after.png"
    (folder / "job.json").write_text(json.dumps(job.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")


def load_job(job_id: str) -> dict | None:
    path = JOBS_DIR / job_id / "job.json"
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))
