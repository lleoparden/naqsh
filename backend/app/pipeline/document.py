"""The editable job document: everything the editor and the exporters need.

One JSON document per job. It holds page settings (register, numeral style, source
size), the plate image name, and a list of layers. A layer is either a text layer
(original text + Arabic per register + box + typography) or a cover patch (flat fill
the user painted over a failed plate region). The document is the single source of
truth for the editor, the SVG export and the PNG export.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from . import shaping, typeset
from .types import BBox

ARABIC_DIGITS = str.maketrans("0123456789", "٠١٢٣٤٥٦٧٨٩")
DEFAULT_FONT = "tajawal"


def to_numerals(text: str, style: str) -> str:
    if style == "arabic-indic":
        return text.translate(ARABIC_DIGITS)
    return text


@dataclass
class LineBox:
    text: str
    size: int
    x: float  # horizontal centre in page pixels
    baseline: float  # baseline y in page pixels
    width: int
    height: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "size": self.size,
            "x": round(self.x, 1),
            "baseline": round(self.baseline, 1),
            "width": self.width,
            "height": self.height,
        }


@dataclass
class Layer:
    id: str
    kind: str  # "text" | "cover"
    box: list[int]
    type: str = "dialogue"
    action: str = "translate"  # translate | keep | skip
    source_text: str = ""
    arabic: dict[str, str] = field(default_factory=dict)
    font_family: str = DEFAULT_FONT
    font_size: int = 0
    lines: list[LineBox] = field(default_factory=list)
    align: str = "center"
    color: list[int] = field(default_factory=lambda: [20, 17, 15])
    z: int = 0
    visible: bool = True
    locked: bool = False
    strategy: str = "muse"
    # Cover layers only
    fill: list[int] = field(default_factory=list)
    # First AI result for this layer, used by "Reset to AI result".
    original: dict[str, Any] = field(default_factory=dict)
    # Free-text name for the layers panel (Spark or the user).
    name: str = ""
    # Cover layers only: "rect" (default) or "ellipse".
    shape: str = "rect"

    @property
    def text_for(self) -> str:
        return self.arabic.get("active", "") or self.source_text

    def active_text(self, register: str) -> str:
        return self.arabic.get(register, "") or self.source_text

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind,
            "type": self.type,
            "action": self.action,
            "source_text": self.source_text,
            "arabic": self.arabic,
            "box": self.box,
            "font_family": self.font_family,
            "font_size": self.font_size,
            "lines": [line.to_dict() for line in self.lines],
            "align": self.align,
            "color": self.color,
            "z": self.z,
            "visible": self.visible,
            "locked": self.locked,
            "strategy": self.strategy,
            "fill": self.fill,
            "original": self.original,
            "name": self.name,
            "shape": self.shape,
        }


@dataclass
class Document:
    id: str
    width: int
    height: int
    register: str = "egyptian"
    numerals: str = "latin"  # latin | arabic-indic
    plate: str = "plate.png"
    composite: str = "composite.png"
    output: str = "output.png"
    source: str = "source.png"
    layers: list[Layer] = field(default_factory=list)

    def layer(self, layer_id: str) -> Layer | None:
        return next((layer for layer in self.layers if layer.id == layer_id), None)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "width": self.width,
            "height": self.height,
            "register": self.register,
            "numerals": self.numerals,
            "images": {
                "plate": self.plate,
                "composite": self.composite,
                "output": self.output,
                "source": self.source,
            },
            "layers": [layer.to_dict() for layer in self.layers],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Document":
        images = data.get("images") or {}
        layers = []
        for item in data.get("layers", []):
            layers.append(
                Layer(
                    id=str(item["id"]),
                    kind=str(item.get("kind") or "text"),
                    box=[int(v) for v in item["box"]],
                    type=str(item.get("type") or "dialogue"),
                    action=str(item.get("action") or "translate"),
                    source_text=str(item.get("source_text") or ""),
                    arabic={k: str(v) for k, v in (item.get("arabic") or {}).items()},
                    font_family=str(item.get("font_family") or DEFAULT_FONT),
                    font_size=int(item.get("font_size") or 0),
                    lines=[
                        LineBox(
                            text=str(line["text"]),
                            size=int(line["size"]),
                            x=float(line["x"]),
                            baseline=float(line["baseline"]),
                            width=int(line.get("width") or 0),
                            height=int(line.get("height") or 0),
                        )
                        for line in item.get("lines", [])
                    ],
                    align=str(item.get("align") or "center"),
                    color=[int(v) for v in item.get("color") or [20, 17, 15]],
                    z=int(item.get("z") or 0),
                    visible=bool(item.get("visible", True)),
                    locked=bool(item.get("locked", False)),
                    strategy=str(item.get("strategy") or "muse"),
                    fill=[int(v) for v in item.get("fill") or []],
                    original=dict(item.get("original") or {}),
                    name=str(item.get("name") or ""),
                    shape=str(item.get("shape") or "rect"),
                )
            )
        return cls(
            id=str(data["id"]),
            width=int(data["width"]),
            height=int(data["height"]),
            register=str(data.get("register") or "egyptian"),
            numerals=str(data.get("numerals") or "latin"),
            plate=images.get("plate", "plate.png"),
            composite=images.get("composite", "composite.png"),
            output=images.get("output", "output.png"),
            source=images.get("source", "source.png"),
            layers=layers,
        )


def layout_text(
    text: str,
    box: list[int],
    *,
    family: str = DEFAULT_FONT,
    register: str = "egyptian",
    numerals: str = "latin",
    action: str = "translate",
    size_limit: int | None = None,
) -> tuple[int, list[LineBox]]:
    """Fit text into a box and return (size, lines with baselines)."""
    # The digits setting applies to any text the page shows: prices are the common
    # case, but dates and quantities should follow the same switch.
    shown = to_numerals(text, numerals)
    bbox = BBox(*box)
    layout = typeset.fit_text(shown, bbox.width, bbox.height, family=family, max_size=size_limit, padding=6)
    lines: list[LineBox] = []
    gap = int(round(layout.size * typeset.LINE_GAP_RATIO))
    shaped = [shaping.shape_line(line, family, layout.size) for line in layout.lines]
    block = sum(line.ink_height for line in shaped) + gap * max(0, len(shaped) - 1)
    top = (bbox.y1 + bbox.y2) / 2 - block / 2
    for line in shaped:
        baseline = top - line.ink[1]
        lines.append(
            LineBox(
                text=line.text,
                size=layout.size,
                x=(bbox.x1 + bbox.x2) / 2,
                baseline=baseline,
                width=line.ink_width,
                height=line.ink_height,
            )
        )
        top += line.ink_height + gap
    return layout.size, lines


def document_from_job(receipt: dict[str, Any]) -> Document:
    """Build the editable document from a finished job receipt."""
    layers: list[Layer] = []
    for index, region in enumerate(receipt.get("regions", [])):
        action = region.get("action", "translate")
        arabic = {"egyptian": region.get("translation_ar", ""), "msa": region.get("translation_ar", "")}
        family = str(region.get("font_family") or "")
        if family not in shaping.FONTS:
            family = typeset.family_for(str(region.get("font_style") or ""), str(region.get("style") or ""))
        layer = Layer(
            id=str(region["id"]),
            kind="text",
            box=[int(v) for v in region["bbox"]],
            type=str(region.get("type") or "dialogue"),
            action=action,
            source_text=str(region.get("source_text") or ""),
            arabic=arabic,
            font_family=family,
            font_size=int(region.get("font_size") or 0),
            color=[int(v) for v in region.get("color") or [20, 17, 15]],
            z=index,
            strategy=str(region.get("strategy") or "muse"),
        )
        layers.append(layer)
    width = int(receipt.get("width") or 0)
    height = int(receipt.get("height") or 0)
    return Document(
        id=str(receipt["id"]),
        width=width,
        height=height,
        register=str(receipt.get("register") or "egyptian"),
        numerals="latin",
        layers=layers,
    )


def layout_document(document: Document, *, only_layer: str | None = None) -> Document:
    """(Re)compute line boxes for every drawable text layer."""
    for layer in document.layers:
        if layer.kind != "text":
            continue
        if only_layer and layer.id != only_layer:
            continue
        text = layer.active_text(document.register)
        layer.font_size, layer.lines = layout_text(
            text,
            layer.box,
            family=layer.font_family,
            register=document.register,
            numerals=document.numerals,
            action=layer.action,
            size_limit=layer.font_size or None,
        )
    return document


def snapshot_layer(layer: Layer) -> dict[str, Any]:
    """The first AI result for a text layer, enough to restore it exactly."""
    return {
        "arabic": dict(layer.arabic),
        "font_family": layer.font_family,
        "font_size": layer.font_size,
        "color": list(layer.color),
        "box": list(layer.box),
        "action": layer.action,
    }


def _snapshot_originals(document: Document) -> None:
    for layer in document.layers:
        if layer.kind == "text" and not layer.original:
            layer.original = snapshot_layer(layer)


def load_document(folder: Path, receipt: dict[str, Any]) -> Document:
    path = folder / "document.json"
    if path.is_file():
        document = layout_document(Document.from_dict(json.loads(path.read_text(encoding="utf-8"))))
        _snapshot_originals(document)
        return document
    document = layout_document(document_from_job(receipt))
    _snapshot_originals(document)
    save_document(folder, document)
    return document


def save_document(folder: Path, document: Document) -> None:
    (folder / "document.json").write_text(
        json.dumps(document.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8"
    )
