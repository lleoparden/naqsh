from PIL import Image

from app.pipeline.regions import _parse_color
from app.pipeline.segment import build_box_prompt, dilate, extend_with_box
from app.pipeline.types import BBox


def test_box_prompt_has_frame_header_and_ids() -> None:
    prompt = build_box_prompt([BBox(10, 20, 110, 60), BBox(200, 220, 300, 260)], 1280, 1920)
    assert prompt.startswith("<0f>1<|box;x1=10;y1=20;x2=110;y2=60;w=1280;h=1920|>")
    assert ",2<|box;x1=200;y1=220;x2=300;y2=260;w=1280;h=1920|>" in prompt


def test_extend_with_box_covers_the_reading_box() -> None:
    mask = Image.new("L", (200, 200), 0)
    mask.paste(255, (60, 60, 100, 100))
    extended = extend_with_box(mask, BBox(40, 50, 140, 120), pad=4)
    assert extended.getpixel((45, 55)) == 255
    assert extended.getpixel((135, 115)) == 255
    assert extended.getbbox() is not None


def test_dilate_grows_the_mask() -> None:
    mask = Image.new("L", (60, 60), 0)
    mask.paste(255, (28, 28, 32, 32))
    grown = dilate(mask, 3)
    assert grown.getbbox() is not None
    assert grown.getbbox()[2] - grown.getbbox()[0] > mask.getbbox()[2] - mask.getbbox()[0]


def test_colour_parsing() -> None:
    assert _parse_color("#1b4f52") == (27, 79, 82)
    assert _parse_color("abc") == (170, 187, 204)
    assert _parse_color(None) == (20, 17, 15)
