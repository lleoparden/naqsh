"""Document model: layout inside a box, numerals, and JSON round-trip."""

from app.pipeline.document import Document, Layer, layout_text, layout_document, to_numerals


def _layer() -> Layer:
    return Layer(
        id="t1",
        kind="text",
        box=[20, 20, 220, 120],
        source_text="HELLO",
        arabic={"egyptian": "أهلاً", "msa": "مرحباً"},
        font_family="tajawal",
    )


def test_document_round_trip() -> None:
    document = Document(id="job", width=300, height=200, layers=[_layer()])
    layout_document(document)
    again = Document.from_dict(document.to_dict())
    assert again.to_dict()["layers"][0]["id"] == "t1"
    assert again.layers[0].arabic["egyptian"] == "أهلاً"
    assert again.width == 300


def test_layout_lines_stay_inside_the_box() -> None:
    size, lines = layout_text("أهلاً بك", [20, 20, 220, 120], family="tajawal")
    assert size > 0 and lines
    for line in lines:
        assert 20 <= line.x <= 220
        assert 10 <= line.baseline <= 130


def test_register_switch_changes_the_layout_text() -> None:
    document = Document(id="job", width=300, height=200, layers=[_layer()])
    layout_document(document)
    egyptian = document.layers[0].lines[0].text
    document.register = "msa"
    layout_document(document)
    assert document.layers[0].lines[0].text != egyptian


def test_numerals_style() -> None:
    assert to_numerals("25", "arabic-indic") == "٢٥"
    assert to_numerals("25", "latin") == "25"
