"""Binary morphology that is fast on full-page masks.

Pillow's ``MaxFilter``/``MinFilter`` run a rank filter, which is O(pixels × k²) and
dominates a menu page (39 s in the profile). OpenCV's ``dilate``/``erode`` with a
square kernel is separable and gives the same result; the equivalence test compares
pixel output before/after on stored jobs.
"""

from __future__ import annotations

import cv2
import numpy as np
from PIL import Image


def _kernel(radius: int) -> np.ndarray:
    size = 2 * radius + 1
    return np.ones((size, size), dtype=np.uint8)


def dilate(mask: Image.Image, radius: int) -> Image.Image:
    if radius <= 0:
        return mask
    array = np.asarray(mask, dtype=np.uint8)
    grown = cv2.dilate(array, _kernel(radius), borderType=cv2.BORDER_REPLICATE)
    return Image.fromarray(grown, mode="L")


def erode(mask: Image.Image, radius: int) -> Image.Image:
    if radius <= 0:
        return mask
    array = np.asarray(mask, dtype=np.uint8)
    shrunk = cv2.erode(array, _kernel(radius), borderType=cv2.BORDER_REPLICATE)
    return Image.fromarray(shrunk, mode="L")


def union_dilated(masks: list[Image.Image], radius: int) -> np.ndarray:
    """Union the masks first, then dilate once: dilation distributes over union."""
    if not masks:
        return np.zeros((1, 1), dtype=np.uint8)
    union = np.zeros_like(np.asarray(masks[0], dtype=np.uint8))
    for mask in masks:
        union = np.maximum(union, np.asarray(mask, dtype=np.uint8))
    if radius <= 0:
        return union
    return cv2.dilate(union, _kernel(radius), borderType=cv2.BORDER_REPLICATE)
