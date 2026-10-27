"""Region policy: what each kind of text does by default."""

from app.pipeline.regions import action_for


def test_translate_defaults() -> None:
    for kind in ("dialogue", "caption", "signage", "menu_item", "title"):
        assert action_for(kind) == "translate"


def test_prices_keep_their_numerals() -> None:
    assert action_for("price") == "keep_numerals"


def test_logos_and_decoration_are_skipped() -> None:
    assert action_for("logo") == "skip"
    assert action_for("decorative") == "skip"


def test_sfx_is_optional_off_by_default() -> None:
    assert action_for("sfx") == "optional"


def test_unknown_type_translates() -> None:
    assert action_for("mystery") == "translate"
    assert action_for("") == "translate"
