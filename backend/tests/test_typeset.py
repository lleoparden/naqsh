from app.pipeline.typeset import available_families, display_text, fit_text


def test_fit_keeps_text_inside_the_box() -> None:
    layout = fit_text("الفصل الأول", 600, 110)
    assert layout.lines
    assert not layout.overflow
    assert layout.height <= int(110 * 0.82)
    assert layout.width <= int(600 * 0.94)


def test_fit_wraps_rather_than_overflowing() -> None:
    layout = fit_text("كل يوم الصبح نفتح المحل قبل الشمس", 260, 220)
    assert len(layout.lines) >= 2
    assert not layout.overflow


def test_fit_flags_a_box_too_small_for_the_text() -> None:
    layout = fit_text("أشوفك بكرة وهجيب معايا الرسومات", 60, 24)
    assert layout.overflow is True
    assert layout.size >= 10


def test_display_text_is_reordered() -> None:
    shaped = display_text("خبز")
    assert shaped
    assert shaped != "خبز"  # presentation forms / visual order differ from logical


def test_bundled_fonts_are_present() -> None:
    families = available_families()
    assert "kufi" in families
    assert "naskh" in families
