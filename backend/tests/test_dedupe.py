from app.pipeline.dedupe import dedupe_regions, iou
from app.pipeline.types import BBox, TextRegion


def _region(rid: str, text: str, box: tuple[int, int, int, int], kind: str = "menu_item") -> TextRegion:
    return TextRegion(
        id=rid,
        source_text=text,
        translation_ar="عربي",
        style="label",
        font_style="bold",
        bbox=BBox(*box),
        type=kind,
        action="translate" if kind != "price" else "keep_numerals",
    )


def test_iou_of_identical_boxes_is_one() -> None:
    assert iou(BBox(0, 0, 10, 10), BBox(0, 0, 10, 10)) == 1.0


def test_identical_text_in_overlapping_boxes_is_dropped() -> None:
    regions = [
        _region("a", "MINT TEA", (10, 10, 200, 40)),
        _region("b", "mint tea", (20, 12, 190, 42)),
    ]
    assert [r.id for r in dedupe_regions(regions)] == ["a"]


def test_identical_text_in_separate_boxes_is_kept() -> None:
    regions = [
        _region("a", "MINT TEA", (10, 10, 200, 40)),
        _region("b", "MINT TEA", (10, 300, 200, 330)),
    ]
    assert len(dedupe_regions(regions)) == 2


def test_price_inside_its_line_is_merged() -> None:
    regions = [
        _region("a", "MINT TEA 10", (10, 10, 300, 40)),
        _region("b", "10", (250, 12, 295, 38), kind="price"),
    ]
    assert [r.id for r in dedupe_regions(regions)] == ["a"]


def test_standalone_price_stays_separate() -> None:
    regions = [
        _region("a", "MINT TEA", (10, 10, 200, 40)),
        _region("b", "10", (250, 12, 295, 38), kind="price"),
    ]
    assert len(dedupe_regions(regions)) == 2
