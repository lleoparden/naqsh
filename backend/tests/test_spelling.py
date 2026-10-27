"""The pipeline must never edit Arabic letters: only dots and whitespace are stripped."""

from app.pipeline.regions import _strip_leaders
from app.pipeline.shaping import shape_line


def test_clean_translation_is_byte_identical() -> None:
    # فلافل 20 is the correct spelling recorded in the MSA menu receipt.
    assert _strip_leaders("فلافل 20") == "فلافل 20"


def test_only_leaders_are_stripped() -> None:
    assert _strip_leaders("فلافل .......... 20") == "فلافل 20"
    assert _strip_leaders("كشري ··· 45") == "كشري 45"
    assert _strip_leaders("أرز باللبن") == "أرز باللبن"


def test_shaping_returns_the_same_logical_text() -> None:
    # Shaping produces glyphs; it must not rewrite the string itself.
    text = "فلالفل"
    assert shape_line(text, "tajawal", 48).text == text


def test_shaping_does_not_normalise_letters() -> None:
    for text in ("فلافل", "فلالفل", "إسكندرية", "شاي"):
        assert shape_line(text, "tajawal", 48).text == text
