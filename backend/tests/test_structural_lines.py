from PIL import Image, ImageDraw

from app.pipeline.plate import _structural_lines


def test_structural_lines_keeps_frames_but_not_text_rows() -> None:
    image = Image.new("RGB", (200, 100), "white")
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 10, 199, 12), fill="black")  # frame line: full span
    draw.rectangle((20, 60, 80, 72), fill="black")  # text-like block: 30% of the row
    mask = _structural_lines(image)
    assert mask[11, 100]
    assert not mask[66, 50]
