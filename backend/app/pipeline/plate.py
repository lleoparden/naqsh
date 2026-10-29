"""Clean-plate stage: erase the original lettering, then keep only the pixels we own.

Muse Image edits by instruction only (no mask parameter) and re-renders the whole
page, which lands with a global offset that varies per generation (-16 px on one
run, -40 px on the next). So the plate is registered to the source first, and then
only the pixels inside the dilated text masks are taken from it. Everything outside
those masks stays byte-for-byte the original artwork.
"""

from __future__ import annotations

import numpy as np
from PIL import Image, ImageFilter

from . import morph

from .meta import Usage, image_edit
from .types import BBox

PLATE_PROMPT = (
    "Remove all lettering from this page: erase the text inside every speech bubble, caption "
    "box, title and label, and repaint those areas with a clean flat fill that matches the "
    "surrounding artwork. Keep everything else identical — same characters, poses, line art, "
    "colours and framing. Do not add new text, objects, logos or signatures. Leave the bubbles "
    "empty and readable as bubbles."
)


RETRY_PROMPT = (
    "This page still shows some of its original lettering. Erase every letter completely — in the "
    "speech bubbles, the caption box and the title — until those areas are empty flat fills that "
    "match the artwork around them. Do not leave faint outlines, shadows or partial letters. Keep "
    "everything else identical: same character, poses, line art, colours and framing. Add no new "
    "text, objects, logos or signatures."
)


def clean_plate(image_png: bytes, *, retry: bool = False) -> tuple[bytes, Usage]:
    return image_edit(image_png, RETRY_PROMPT if retry else PLATE_PROMPT)


def _gray(image: Image.Image, step: int) -> np.ndarray:
    small = image.convert("L").resize((max(8, image.width // step), max(8, image.height // step)), Image.BILINEAR)
    return np.asarray(small, dtype=np.float64)


def _valid_mask(shape: tuple[int, int], exclude: list[BBox], step: int, grow: int = 3) -> np.ndarray:
    valid = np.ones(shape, dtype=bool)
    for box in exclude:
        x1, y1 = max(0, int(box.x1 / step) - grow), max(0, int(box.y1 / step) - grow)
        x2, y2 = int(box.x2 / step) + grow, int(box.y2 / step) + grow
        valid[y1:y2, x1:x2] = False
    if valid.sum() < 200:
        valid[:] = True
    return valid


def _score(a: np.ndarray, b: np.ndarray, dx: int, dy: int, valid: np.ndarray) -> float:
    """Mean squared difference after shifting b by (dx, dy), outside the text boxes."""
    shifted = np.roll(np.roll(b, dy, axis=0), dx, axis=1)
    diff = (a - shifted)[valid]
    return float(np.mean(diff * diff))


def _edges(image: Image.Image, scale: float = 0.5) -> np.ndarray:
    """Edge magnitude at half resolution; robust to colour shifts between renders."""
    size = (max(16, int(image.width * scale)), max(16, int(image.height * scale)))
    small = image.convert("L").resize(size, Image.BILINEAR).filter(ImageFilter.FIND_EDGES)
    return np.asarray(small, dtype=np.float64)


def _phase_shift(a: np.ndarray, b: np.ndarray) -> tuple[int, int]:
    """Shift of b relative to a from phase correlation with a Hann window."""
    height, width = a.shape
    window = np.hanning(height)[:, None] * np.hanning(width)[None, :]
    fa = np.fft.rfft2((a - a.mean()) * window)
    fb = np.fft.rfft2((b - b.mean()) * window)
    cross = fa * np.conj(fb)
    cross /= np.abs(cross) + 1e-9
    corr = np.fft.irfft2(cross, s=(height, width))
    peak = np.unravel_index(int(np.argmax(corr)), corr.shape)
    dy, dx = int(peak[0]), int(peak[1])
    if dy > height // 2:
        dy -= height
    if dx > width // 2:
        dx -= width
    return dx, dy


def estimate_shift(source: Image.Image, plate: Image.Image, exclude: list[BBox]) -> tuple[int, int]:
    """Offset (dx, dy) that moves the plate onto the source, in source pixels.

    Coarse: phase correlation of edge maps (a re-render changes flat colour slightly
    but keeps the line art). Fine: local search on full-resolution pixels, scored
    only outside the lettering boxes, where the two images should be identical.
    """
    plate = plate.resize(source.size, Image.LANCZOS)
    side = np.array(source.size) / 2.0
    coarse_dx, coarse_dy = _phase_shift(_edges(source), _edges(plate))
    coarse_dx, coarse_dy = int(round(coarse_dx / 0.5)), int(round(coarse_dy / 0.5))
    coarse_dx = int(np.clip(coarse_dx, -side[0] / 8, side[0] / 8))
    coarse_dy = int(np.clip(coarse_dy, -side[1] / 8, side[1] / 8))

    # Refine at half resolution: a quarter of the pixels for the same search, and the
    # ring-residual report catches it if ±2 px is not good enough.
    step = 2
    a_half = _gray(source, step)
    b_half = _gray(plate, step)
    valid_half = _valid_mask(a_half.shape, exclude, step, grow=2)
    refined = (coarse_dx // step, coarse_dy // step, float("inf"))
    for dy in range(coarse_dy // step - 4, coarse_dy // step + 5):
        for dx in range(coarse_dx // step - 4, coarse_dx // step + 5):
            score = _score(a_half, b_half, dx, dy, valid_half)
            if score < refined[2]:
                refined = (dx, dy, score)
    return int(refined[0] * step), int(refined[1] * step)


def measure_dirty_plate(plate: Image.Image, boxes: list[BBox], *, tolerance: float = 60.0) -> float:
    """Fraction of ink-like pixels inside the lettering boxes of a supposedly clean plate.

    A clean plate shows only the flat fill there; leftover strokes mean the edit did
    not finish the job. Used to decide whether to regenerate the plate once.
    """
    if not boxes:
        return 0.0
    canvas = np.asarray(plate.convert("RGB"), dtype=np.int16)
    scores: list[float] = []
    for box in boxes:
        x1 = max(0, min(plate.width - 8, box.x1))
        y1 = max(0, min(plate.height - 8, box.y1))
        x2 = max(x1 + 8, min(plate.width, box.x2))
        y2 = max(y1 + 8, min(plate.height, box.y2))
        region = canvas[y1:y2, x1:x2].reshape(-1, 3)
        if region.size == 0:
            continue
        fill = np.median(region, axis=0)
        scores.append(float((np.abs(region - fill).max(axis=1) > tolerance).mean()))
    return max(scores, default=0.0)


def apply_shift(plate: Image.Image, size: tuple[int, int], dx: int, dy: int) -> Image.Image:
    plate_resized = plate.resize(size, Image.LANCZOS)
    return plate_resized.transform(
        size,
        Image.AFFINE,
        (1, 0, -dx, 0, 1, -dy),
        resample=Image.BICUBIC,
    )


def alignment_report(
    source: Image.Image,
    plate: Image.Image,
    masks: list[Image.Image],
    *,
    inner: int = 8,
    outer: int = 24,
) -> dict[str, object]:
    """Mean |difference| in a ring just outside each mask, after registration.

    Text has been erased inside the masks, so the ring is where the two images should
    agree if the plate is aligned. A large ring residual means the plate is shifted or
    scaled and the composite will seam, regardless of how clean the edit was.
    """
    original = np.asarray(source.convert("RGB"), dtype=np.int16)
    replacement = np.asarray(plate.convert("RGB"), dtype=np.int16)
    per_region: list[float] = []
    for index, mask in enumerate(masks):
        grown_outer = morph.dilate(mask, outer)
        grown_inner = morph.dilate(mask, inner)
        ring = (np.asarray(grown_outer, dtype=np.uint8) > 127) & ~(np.asarray(grown_inner, dtype=np.uint8) > 127)
        if ring.sum() < 50:
            continue
        diff = np.abs(original - replacement).max(axis=2)[ring]
        per_region.append(float(diff.mean()))
    return {
        "ring_mean_abs_diff": round(float(np.mean(per_region)), 2) if per_region else None,
        "ring_max_abs_diff": round(float(np.max(per_region)), 2) if per_region else None,
        "ring_per_region": [round(v, 2) for v in per_region],
        "ring_band_px": [inner, outer],
    }


def _structural_lines(image: Image.Image) -> np.ndarray:
    """Pixels on long, near-horizontal/vertical dark lines (panel borders, frames).

    Muse Image often redraws a caption box or frame slightly shifted. Replacing those
    pixels with the plate moves the frame on the after side, which is visible at the
    before/after divider. Long straight dark runs are structure, not lettering, so the
    composite restores the source there.
    """
    gray = np.asarray(image.convert("L"), dtype=np.uint8)
    dark = gray < 70
    rows = np.where(dark.mean(axis=1) > 0.45)[0]
    cols = np.where(dark.mean(axis=0) > 0.45)[0]
    mask = np.zeros_like(dark, dtype=bool)
    if rows.size:
        mask[rows, :] = True
    if cols.size:
        mask[:, cols] = True
    if rows.size or cols.size:
        grown = morph.dilate(Image.fromarray((mask * 255).astype(np.uint8)), 16)
        return np.asarray(grown) > 127
    return mask


def composite(
    source: Image.Image,
    plate: Image.Image,
    masks: list[Image.Image],
    *,
    dilation: int = 8,
    preserve_lines: bool = True,
) -> tuple[Image.Image, dict[str, float]]:
    """Take plate pixels only inside the (dilated) text masks."""
    if not masks:
        raise ValueError("compositing needs at least one mask")

    # One dilation of the union instead of one per mask: dilation distributes over
    # union, so the result is identical and the menu page stops spending seconds here.
    coverage = morph.union_dilated(masks, dilation)

    inside = coverage > 127
    original = np.asarray(source.convert("RGB"), dtype=np.uint8)
    replacement = np.asarray(plate.convert("RGB"), dtype=np.uint8)
    output = original.copy()
    output[inside] = replacement[inside]
    if preserve_lines:
        lines = _structural_lines(source)
        output[lines] = original[lines]

    outside = ~inside
    diff_inside = float(np.abs(original.astype(np.int16) - replacement.astype(np.int16))[inside].mean()) if inside.any() else 0.0
    untouched = float(np.abs(original.astype(np.int16) - output.astype(np.int16))[outside].mean()) if outside.any() else 0.0
    stats = {
        "coverage_ratio": round(float(inside.mean()), 4),
        "mean_abs_diff_inside": round(diff_inside, 2),
        "outside_untouched_mean_diff": round(untouched, 4),
    }
    return Image.fromarray(output, mode="RGB"), stats
