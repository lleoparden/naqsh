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
from concurrent.futures import ThreadPoolExecutor
import json
import re
import logging
import time
import uuid
from pathlib import Path

from PIL import Image, ImageDraw

from . import coverage as coverage_stage
from .dedupe import dedupe_regions
from . import leaders as leaders_stage
from . import plate as plate_stage
from . import regions as regions_stage
from . import render as render_stage
from . import residual as residual_stage
from . import segment as segment_stage
from . import selfcheck as selfcheck_stage
from . import typeset
from .background import build_assets
from .meta import MetaAPIError
from .meta import spark_translate as retranslate_line
from .types import BBox, Layout, PageJob, TextRegion

log = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[3]
JOBS_DIR = REPO_ROOT / "backend" / ".cache" / "jobs"
LEADER_HINT = re.compile(r"[.·•…]{3,}")


def _ms(started: float) -> int:
    return int(round((time.perf_counter() - started) * 1000))


def family_for(font_style: str, style: str = "") -> str:
    """Map Spark's style words to a bundled OFL family (see typeset.family_for)."""
    return typeset.family_for(font_style, style)


def repaint_regions(regions: list[TextRegion]) -> list[TextRegion]:
    """Regions whose background Naqsh may repaint.

    Skipped (logos, decoration) and optional (SFX, off by default) regions keep the
    original pixels, so they are left out of segmentation, verification and rendering.
    """
    return [region for region in regions if region.action not in ("skip", "optional")]


def text_for_region(region: TextRegion) -> str:
    """What to draw: the Arabic translation, or the original numerals for prices."""
    if region.action == "keep_numerals":
        return region.source_text or region.translation_ar
    return region.translation_ar


def _container_for(reading_box: BBox, mask: Image.Image) -> BBox:
    """The area text may fill: usually the reading box, or a bubble's interior.

    Spark's reading box is already tight around the lettering, so it is the safe
    default. Only when the mask is clearly a container around that box (a bubble or a
    panel, much larger than the text block) is its eroded interior used, intersected
    with the reading box plus a margin. That keeps text off the outline without
    shrinking a menu line to half its width.
    """
    bounds = mask.getbbox()
    if not bounds:
        return reading_box
    candidate = BBox(*bounds)
    reading_area = max(1, reading_box.width * reading_box.height)
    mask_area = candidate.width * candidate.height
    if mask_area < 1.4 * reading_area:
        # The mask may be the box itself (a caption bar). When it covers a decent
        # share of the reading box, trust it and inset a little: fitting to the loose
        # reading box is what lets caption text overflow a short bar.
        if mask_area >= 0.45 * reading_area:
            pad = max(3, int(0.06 * min(candidate.width, candidate.height)))
            return BBox(
                max(reading_box.x1, candidate.x1 + pad),
                max(reading_box.y1, candidate.y1 + pad),
                min(reading_box.x2, candidate.x2 - pad),
                min(reading_box.y2, candidate.y2 - pad),
            )
        return reading_box

    interior = segment_stage.inner_box(mask)
    if interior is None:
        return reading_box
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
    if x2 - x1 < 0.8 * reading_box.width or y2 - y1 < 0.8 * reading_box.height:
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


def run_page_job(image_bytes: bytes, register: str = "egyptian", *, background_layers: bool = False) -> PageJob:
    job_id = uuid.uuid4().hex[:12]
    folder = JOBS_DIR / job_id
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "source.png").write_bytes(image_bytes)

    with Image.open(io.BytesIO(image_bytes)) as opened:
        source = opened.convert("RGB")
    width, height = source.size
    job = PageJob(id=job_id, register=register, width=width, height=height)
    job._started = time.perf_counter()
    job.artifacts["source"] = "source.png"

    # 1. Read + translate ---------------------------------------------------------
    started = time.perf_counter()
    regions, usage = regions_stage.read_regions(image_bytes, width, height, register)
    before_dedupe = len(regions)
    regions = dedupe_regions(regions)
    job.regions = regions
    job.add_stage(
        "read",
        _ms(started),
        usage.spark_cost(),
        **usage.to_dict(),
        regions=len(regions),
        regions_before_dedupe=before_dedupe,
        duplicates_dropped=before_dedupe - len(regions),
    )
    if not regions:
        job.warnings.append("no text regions found")
        _finish(job, folder, source, source)
        return job
    # Skipped (logo, decoration) and optional (SFX, off by default) regions keep their
    # original pixels: they never enter segmentation, verification or rendering.
    repaint = repaint_regions(regions)
    job.add_stage(
        "policy",
        0,
        0.0,
        translated=[r.id for r in repaint],
        skipped=[r.id for r in regions if r.action == "skip"],
        optional=[r.id for r in regions if r.action == "optional"],
        keep_numerals=[r.id for r in regions if r.action == "keep_numerals"],
    )
    if not repaint:
        job.warnings.append("every region was skipped by policy")
        _finish(job, folder, source, source)
        return job

    # 2. Segment + ink-derived coverage, concurrently with the clean plate ----------
    # SAM (segment) and Muse Image (clean plate) are independent HTTP calls on the same
    # bytes with no shared state, so the page waits for the slower one, not the sum.
    started = time.perf_counter()
    plate_started = time.perf_counter()
    with ThreadPoolExecutor(max_workers=2) as pool:
        segment_future = pool.submit(segment_stage.segment_regions, image_bytes, repaint, width, height)
        plate_future = pool.submit(plate_stage.clean_plate, image_bytes)
        masks, sam_usage, warnings = segment_future.result()
        job.warnings.extend(warnings)
    coverage: dict[str, Image.Image] = {}
    leader_runs: list[dict] = []
    for region in repaint:
        mask = masks.get(region.id)
        if mask is None:
            continue
        region.container = _container_for(region.bbox, mask)
        coverage[region.id], _area = coverage_stage.coverage_for(source, mask, region.bbox)
        leader = None
        if LEADER_HINT.search(region.source_text or ""):
            # Only lines whose OCR text shows a dot run can have leaders; this keeps a
            # decorative rule elsewhere on the page from being erased by mistake.
            leader = leaders_stage.find_leaders(source, region.bbox, mask)
        if leader is not None:
            # Dotted menu leaders are punctuation, so the text mask misses them; add
            # their bbox to the repaint area or they survive localization.
            ImageDraw.Draw(coverage[region.id]).rectangle(leader.bbox.to_list(), fill=255)
            leader_runs.append(
                {
                    "region": region.id,
                    "bbox": leader.bbox.to_list(),
                    "dots": leader.dots,
                    "spacing": leader.spacing,
                }
            )
        name = f"mask-{region.id}.png"
        mask.save(folder / name)
        region.mask_path = name
    job.add_stage(
        "segment",
        _ms(started),
        sam_usage.images * 2.50 / 1000,
        masks=len(masks),
        concepts="box prompts + ink extent",
        leaders=leader_runs,
    )
    overlay = segment_stage.overlay_preview(source, coverage)
    overlay.save(folder / "masks-overlay.png")
    job.artifacts["mask_overlay"] = "masks-overlay.png"

        # 3. Clean plate (the pool waited for the Muse Image call on exit) ------------
    plate_raw, _plate_usage = plate_future.result()
    plate_ms = _ms(plate_started)
    with Image.open(io.BytesIO(plate_raw)) as opened:
        plate_image = opened.convert("RGB")
    plate_size = plate_image.size
    (folder / "plate-raw.png").write_bytes(plate_raw)
    job.artifacts["plate_raw"] = "plate-raw.png"
    job.add_stage(
        "clean_plate",
        plate_ms,
        0.01,
        images=1,
        plate_size=list(plate_size),
        concurrent_with=["segment"],
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
    strategies: dict[str, str] = {region.id: "muse" for region in repaint}
    verify_cost = 0.0
    try:
        verdicts, cost, summary = _check(composite, repaint)
        verify_cost += cost
        remaining = [v.region_id for v in verdicts if v.residual]
        notes = summary["notes"]
        job.add_stage("verify", _ms(started), verify_cost, **summary)

        if remaining:
            retry_started = time.perf_counter()
            retry_raw, _ = plate_stage.clean_plate(image_bytes, retry=True)
            with Image.open(io.BytesIO(retry_raw)) as opened:
                retry_image = opened.convert("RGB")
            retry_dx, retry_dy = plate_stage.estimate_shift(source, retry_image, [r.bbox for r in repaint])
            retry_aligned = plate_stage.apply_shift(retry_image, (width, height), retry_dx, retry_dy)
            retry_composite, retry_stats, retry_flat = _compose(source, retry_aligned, coverage, masks)
            verdicts2, cost2, summary2 = _check(retry_composite, repaint)
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
                for region in repaint:
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

    # 6. Background layers (scenery + speech bubbles), optional ---------------------
    if background_layers:
        _background_stage(job, folder, image_bytes, composite, repaint, source.width, source.height)
    else:
        job.add_stage("background", 0, 0.0, enabled=False, skipped="disabled by request")

    # 7. Typeset + render ---------------------------------------------------------
    started = time.perf_counter()
    layouts: dict[str, Layout] = {}
    colors: dict[str, tuple[int, int, int]] = {}
    for region in repaint:
        region.font_family = family_for(region.font_style, region.style)
        container = region.container or region.bbox
        layout = typeset.fit_text(
            text_for_region(region),
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
    final = render_stage.draw_regions(composite, repaint, layouts, color_of=colors)
    final.save(folder / "output.png")
    job.artifacts["output"] = "output.png"
    job.add_stage(
        "typeset",
        _ms(started),
        0.0,
        regions=len(layouts),
        strategies=strategies,
        types={r.id: r.type for r in repaint},
    )

    # 7. Visual self-check: one look, one fix pass, one re-check -------------------
    started = time.perf_counter()
    selfcheck_cost = 0.0
    try:
        verdicts, sc_usage, _raw = selfcheck_stage.check_render(final, repaint)
        selfcheck_cost += sc_usage.spark_cost()
        flagged = [v for v in verdicts if not v.ok]
        fixed: list[str] = []
        retranslated: list[str] = []
        if flagged:
            for verdict in flagged:
                if verdict.issue != "bad_translation":
                    continue
                region = next((r for r in repaint if r.id == verdict.region_id), None)
                if region is None:
                    continue
                new_text, translate_usage = retranslate_line(
                    region.source_text,
                    region.translation_ar,
                    verdict.note or "translation does not match the source",
                    regions_stage.REGISTERS.get(register, ""),
                )
                selfcheck_cost += translate_usage.spark_cost()
                if new_text and new_text != region.translation_ar:
                    region.translation_ar = new_text
                    box = region.container or region.bbox
                    layout = typeset.fit_text(new_text, box.width, box.height, family=region.font_family)
                    region.font_size = layout.size
                    region.lines = layout.lines
                    layouts[region.id] = layout
                    retranslated.append(region.id)

            fixed = selfcheck_stage.apply_fix(
                repaint,
                layouts,
                [v for v in flagged if v.issue != "bad_translation"],
                typeset.fit_text,
            )
            final = render_stage.draw_regions(composite, repaint, layouts, color_of=colors)
            final.save(folder / "output.png")
            verdicts_after, after_usage, _ = selfcheck_stage.check_render(final, repaint)
            selfcheck_cost += after_usage.spark_cost()
            still = [v.region_id for v in verdicts_after if not v.ok]
        else:
            still = []
        job.add_stage(
            "selfcheck",
            _ms(started),
            selfcheck_cost,
            flagged=[v.region_id for v in flagged],
            issues={v.region_id: v.issue for v in flagged},
            fixed=fixed,
            retranslated=retranslated,
            still_flagged=still,
        )
    except MetaAPIError as exc:
        job.warnings.append(f"visual self-check unavailable: {exc}")
        job.add_stage("selfcheck", _ms(started), 0.0, error=str(exc))

    _finish(job, folder, source, final)
    return job



def _background_stage(
    job: PageJob,
    folder: Path,
    image_bytes: bytes,
    composite: Image.Image,
    regions: list[TextRegion],
    width: int,
    height: int,
) -> None:
    """Build scene/bubble layers; never let a background failure fail the job."""
    started = time.perf_counter()
    try:
        summary = build_assets(
            folder,
            image_bytes,
            composite,
            [
                {
                    "id": region.id,
                    "bbox": [region.bbox.x1, region.bbox.y1, region.bbox.x2, region.bbox.y2],
                    "type": region.type,
                    "name": getattr(region, "name", "") or region.id,
                }
                for region in regions
            ],
            width,
            height,
        )
        usage = summary.get("usage")
        cost = (usage.images * 2.50 / 1000) if usage else 0.0
        counts = summary["counts"]
        job.add_stage(
            "background",
            _ms(started),
            cost,
            bubbles=counts["bubbles"],
            sam=counts["sam"],
            box_fallback=counts["box_fallback"],
            fallback_suppressed=counts.get("fallback_suppressed", False),
        )
        logging.getLogger("uvicorn.error").info(
            "%s: background bubbles=%s sam=%s box_fallback=%s fallback_suppressed=%s",
            job.id,
            counts["bubbles"],
            counts["sam"],
            counts["box_fallback"],
            counts.get("fallback_suppressed", False),
        )
    except Exception as exc:  # single-plate fallback, recorded and logged
        job.warnings.append(f"background layers unavailable: {exc}")
        job.add_stage("background", _ms(started), 0.0, error=str(exc)[:300])
        logging.getLogger("uvicorn.error").warning("%s: background layers failed: %s", job.id, exc)


def _finish(job: PageJob, folder: Path, source: Image.Image, final: Image.Image) -> None:
    """Write the side-by-side evidence image and the job receipt."""
    combo = Image.new("RGB", (source.width * 2 + 24, source.height), "white")
    combo.paste(source, (0, 0))
    combo.paste(final, (source.width + 24, 0))
    combo.save(folder / "before-after.png")
    job.artifacts["before_after"] = "before-after.png"
    started = getattr(job, "_started", None)
    if started is not None:
        job.elapsed_ms = int(round((time.perf_counter() - started) * 1000))
    (folder / "job.json").write_text(json.dumps(job.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")


def load_job(job_id: str) -> dict | None:
    path = JOBS_DIR / job_id / "job.json"
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))