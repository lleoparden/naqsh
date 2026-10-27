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

    a_full = _gray(source, 1)
    b_full = _gray(plate, 1)
    valid_full = _valid_mask(a_full.shape, exclude, 1, grow=6)
    refined = (coarse_dx, coarse_dy, float("inf"))
    for dy in range(coarse_dy - 6, coarse_dy + 7):
        for dx in range(coarse_dx - 6, coarse_dx + 7):
            score = _score(a_full, b_full, dx, dy, valid_full)
            if score < refined[2]:
                refined = (dx, dy, score)
    return int(refined[0]), int(refined[1])


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


def composite(
    source: Image.Image,
    plate: Image.Image,
    masks: list[Image.Image],
    *,
    dilation: int = 8,
) -> tuple[Image.Image, dict[str, float]]:
    """Take plate pixels only inside the (dilated) text masks."""
    if not masks:
        raise ValueError("compositing needs at least one mask")

    coverage = np.zeros((source.height, source.width), dtype=np.uint8)
    for mask in masks:
        # MaxFilter(1) divides by zero inside Pillow, so a zero dilation means "as is".
        grown = mask.filter(ImageFilter.MaxFilter(2 * dilation + 1)) if dilation > 0 else mask
        coverage = np.maximum(coverage, np.asarray(grown, dtype=np.uint8))

    inside = coverage > 127
    original = np.asarray(source.convert("RGB"), dtype=np.uint8)
    replacement = np.asarray(plate.convert("RGB"), dtype=np.uint8)
    output = original.copy()
    output[inside] = replacement[inside]

    outside = ~inside
    diff_inside = float(np.abs(original.astype(np.int16) - replacement.astype(np.int16))[inside].mean()) if inside.any() else 0.0
    untouched = float(np.abs(original.astype(np.int16) - output.astype(np.int16))[outside].mean()) if outside.any() else 0.0
    stats = {
        "coverage_ratio": round(float(inside.mean()), 4),
        "mean_abs_diff_inside": round(diff_inside, 2),
        "outside_untouched_mean_diff": round(untouched, 4),
    }
    return Image.fromarray(output, mode="RGB"), stats
