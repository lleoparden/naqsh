"""Unit tests for the self-check fix pass and summary helpers."""

from app.pipeline.selfcheck import Verdict, apply_fix, summarise
from app.pipeline.types import BBox, Layout, TextRegion


def _region(size: int = 80) -> TextRegion:
    return TextRegion(
        id="t1",
        source_text="FRESH BREAD?",
        translation_ar="عيش طازة؟",
        style="speech",
        font_style="bold",
        bbox=BBox(100, 100, 300, 200),
        font_family="tajawal",
    )


def test_apply_fix_shrinks_flagged_regions() -> None:
    region = _region()
    layout = Layout(lines=["عيش طازة؟"], size=70, line_height=84, width=180, height=80)
    layouts = {"t1": layout}
    fixed = apply_fix([region], layouts, [Verdict("t1", "overflow", "runs past the balloon")], _fit)
    assert fixed == ["t1"]
    assert layouts["t1"].size < 70


def test_bad_translation_is_left_to_the_caller() -> None:
    region = _region()
    layouts = {"t1": Layout(lines=["x"], size=70, line_height=84, width=10, height=10)}
    fixed = apply_fix([region], layouts, [Verdict("t1", "bad_translation", "wrong meaning")], _fit)
    assert fixed == []
    assert layouts["t1"].size == 70


def test_summary_lists_only_problems() -> None:
    summary = summarise([Verdict("t1", "none", "fine"), Verdict("t2", "clipping", "cut")])
    assert summary["flagged"] == ["t2"]
    assert summary["issues"] == {"t2": "clipping"}


def _fit(text, width, height, *, family, max_size=None):
    # A deterministic stand-in for fit_text in unit tests.
    return Layout(lines=[text], size=max(10, int((max_size or 70) * 0.8)), line_height=60, width=100, height=50)
