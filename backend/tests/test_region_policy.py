from app.pipeline.job import repaint_regions, text_for_region
from app.pipeline.types import BBox, TextRegion


def _region(action: str, translation: str = "عربي", source: str = "SOURCE") -> TextRegion:
    return TextRegion(
        id=action,
        source_text=source,
        translation_ar=translation,
        style="speech",
        font_style="bold",
        bbox=BBox(0, 0, 10, 10),
        action=action,
    )


def test_skip_and_optional_regions_keep_original_pixels() -> None:
    regions = [_region("translate"), _region("skip"), _region("optional"), _region("keep_numerals")]
    kept = repaint_regions(regions)
    assert [r.action for r in kept] == ["translate", "keep_numerals"]


def test_prices_draw_the_original_numerals() -> None:
    price = _region("keep_numerals", translation="٢٠", source="20")
    assert text_for_region(price) == "20"


def test_translated_regions_draw_arabic() -> None:
    region = _region("translate", translation="كشري", source="KOSHARY")
    assert text_for_region(region) == "كشري"
