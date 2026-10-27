from PIL import Image, ImageDraw

from app.pipeline.plate import composite, estimate_shift
from app.pipeline.types import BBox


def _page(offset: tuple[int, int] = (0, 0)) -> Image.Image:
    image = Image.new("RGB", (400, 300), "white")
    draw = ImageDraw.Draw(image)
    draw.rectangle([40 + offset[0], 40 + offset[1], 240 + offset[0], 140 + offset[1]], fill="black")
    draw.ellipse([260 + offset[0], 180 + offset[1], 360 + offset[0], 260 + offset[1]], fill="gray")
    return image


def test_recovers_a_known_shift() -> None:
    source = _page()
    plate = _page((9, -7))
    dx, dy = estimate_shift(source, plate, [])
    # The plate's content sits at +9/-7; aligning it back needs the opposite move.
    assert abs(dx + 9) <= 2
    assert abs(dy - 7) <= 2


def test_composite_only_touches_the_mask() -> None:
    source = Image.new("RGB", (120, 120), (255, 255, 255))
    plate = Image.new("RGB", (120, 120), (0, 0, 0))
    mask = Image.new("L", (120, 120), 0)
    mask.paste(255, (20, 20, 60, 60))

    result, stats = composite(source, plate, [mask], dilation=0)
    assert result.getpixel((40, 40)) == (0, 0, 0)
    assert result.getpixel((100, 100)) == (255, 255, 255)
    assert stats["coverage_ratio"] > 0.05
