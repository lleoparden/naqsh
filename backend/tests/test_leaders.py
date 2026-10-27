from PIL import Image, ImageDraw

from app.pipeline.leaders import find_leaders
from app.pipeline.types import BBox


def _page(with_dots: bool) -> tuple[Image.Image, Image.Image]:
    image = Image.new("RGB", (600, 200), (246, 240, 226))
    draw = ImageDraw.Draw(image)
    draw.text((40, 70), "KOSHARY", fill=(20, 20, 20))
    if with_dots:
        # Printed leaders on this menu are dark teal, not black; black is reserved for
        # the frame, which must not be mistaken for leaders.
        for x in range(150, 420, 22):
            draw.ellipse([x, 86, x + 5, 91], fill=(30, 70, 85))
    draw.text((470, 70), "45", fill=(20, 20, 20))
    mask = Image.new("L", image.size, 0)
    ImageDraw.Draw(mask).rectangle([20, 40, 580, 150], fill=255)
    return image, mask


def test_detects_a_dotted_leader_run() -> None:
    image, mask = _page(True)
    run = find_leaders(image, BBox(30, 60, 540, 110), mask)
    assert run is not None
    assert run.dots >= 5
    assert run.bbox.width > 100


def test_returns_none_without_dots() -> None:
    image, mask = _page(False)
    assert find_leaders(image, BBox(30, 60, 540, 110), mask) is None


def test_ignores_scattered_noise() -> None:
    image, mask = _page(False)
    draw = ImageDraw.Draw(image)
    for x, y in [(120, 60), (260, 130), (400, 50), (520, 100)]:
        draw.ellipse([x, y, x + 4, y + 4], fill=(30, 30, 30))
    assert find_leaders(image, BBox(30, 60, 540, 110), mask) is None
