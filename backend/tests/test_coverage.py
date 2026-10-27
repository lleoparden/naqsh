from PIL import Image, ImageDraw

from app.pipeline.coverage import coverage_for, ink_extent
from app.pipeline.plate import alignment_report
from app.pipeline.residual import flat_fill, region_is_flat
from app.pipeline.types import BBox


def _bubble_page() -> tuple[Image.Image, Image.Image]:
    image = Image.new("RGB", (300, 220), (20, 60, 80))
    draw = ImageDraw.Draw(image)
    # Striped background so a registration error is visible in the ring outside the mask.
    for x in range(0, 300, 18):
        draw.line([(x, 0), (x, 220)], fill=(120, 70, 40), width=6)
    draw.ellipse([40, 30, 260, 190], fill=(250, 244, 228), outline=(10, 10, 10), width=4)
    draw.text((95, 90), "HELLO", fill=(170, 90, 60))
    mask = Image.new("L", image.size, 0)
    ImageDraw.Draw(mask).ellipse([40, 30, 260, 190], fill=255)
    return image, mask


def test_ink_extent_grows_beyond_the_reading_box() -> None:
    image, mask = _bubble_page()
    reading = BBox(95, 86, 160, 96)  # deliberately too short, like Spark's box
    extent = ink_extent(image, mask, reading)
    assert extent is not None
    assert extent.y2 > reading.y2  # the glyphs reach below the guessed box


def test_coverage_covers_the_ink() -> None:
    image, mask = _bubble_page()
    reading = BBox(90, 85, 200, 110)
    coverage, _area = coverage_for(image, mask, reading)
    extent = ink_extent(image, mask, reading)
    assert extent is not None
    assert coverage.getpixel((extent.x1 + 2, extent.y2 - 2)) == 255


def test_alignment_report_is_small_when_the_plate_matches() -> None:
    image, mask = _bubble_page()
    report = alignment_report(image, image.copy(), [mask])
    assert report["ring_mean_abs_diff"] == 0.0


def test_alignment_report_notices_a_shift() -> None:
    image, mask = _bubble_page()
    shifted = image.transform(image.size, Image.AFFINE, (1, 0, -6, 0, 1, 4))
    report = alignment_report(image, shifted, [mask])
    assert report["ring_mean_abs_diff"] > 0.5


def test_flat_fill_repaints_ghost_inside_a_flat_bubble() -> None:
    image, mask = _bubble_page()
    coverage = mask.copy()
    assert region_is_flat(image, mask)
    filled, changed = flat_fill(image, mask, coverage)
    assert changed is True
    # The ghost stroke pixel is gone; the bubble fill remains.
    assert filled.getpixel((115, 100)) != (170, 90, 60)


def test_textured_region_is_not_flat() -> None:
    image = Image.new("RGB", (120, 120), (0, 0, 0))
    draw = ImageDraw.Draw(image)
    for x in range(0, 120, 4):
        draw.line([(x, 0), (x, 120)], fill=(200, 200, 200), width=2)
    mask = Image.new("L", (120, 120), 255)
    assert region_is_flat(image, mask) is False
