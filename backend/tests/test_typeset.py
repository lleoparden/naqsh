from app.pipeline.shaping import FONTS, available_families, measure, shape_line
from app.pipeline.typeset import family_for, fit_text


def test_bundled_fonts_are_present() -> None:
    families = available_families()
    assert {"tajawal", "tajawal-bold", "naskh"} <= set(families)
    for name in families:
        assert FONTS[name][0].endswith(".ttf")


def test_shaping_joins_letters() -> None:
    joined = shape_line("خبز", "tajawal", 64)
    isolated = sum(shape_line(char, "tajawal", 64).width for char in "خبز")
    # Cursive joining pulls the letters into one word; isolated forms are wider.
    assert joined.ink_width < isolated


def test_diacritics_count_towards_the_ink_box() -> None:
    plain = measure("خبز", "tajawal", 64)
    marked = measure("خَبّز", "tajawal", 64)
    assert marked[1] >= plain[1]


def test_fit_keeps_every_line_inside_the_box() -> None:
    layout = fit_text("الفصل الأول", 420, 110)
    assert layout.lines
    assert not layout.overflow
    for line in layout.lines:
        width, height = measure(line, "tajawal", layout.size)
        assert width <= 420
    assert layout.height <= int(110 * 0.88)


def test_fit_wraps_long_text() -> None:
    layout = fit_text("كل يوم الصبح نفتح المحل قبل الشمس", 220, 240)
    assert len(layout.lines) >= 2
    assert not layout.overflow


def test_two_lines_are_balanced() -> None:
    layout = fit_text("شاي بالنعناع مع بسكوت", 300, 200)
    if len(layout.lines) == 2:
        widths = [measure(line, "tajawal", layout.size)[0] for line in layout.lines]
        assert abs(widths[0] - widths[1]) <= max(widths) * 0.45


def test_overflow_is_flagged_when_the_box_is_too_small() -> None:
    layout = fit_text("أشوفك بكرة وهجيب معايا الرسومات", 48, 22)
    assert layout.overflow is True
    assert layout.size >= 10


def test_style_mapping_uses_rights_clean_families() -> None:
    assert family_for("bold rounded uppercase sans") == "tajawal-bold"
    assert family_for("serif print") == "naskh"
    assert family_for("handwritten chalk") in {"tajawal", "tajawal-bold"}
