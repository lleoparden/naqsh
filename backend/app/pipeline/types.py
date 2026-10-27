"""Typed shapes shared by the pipeline stages.

Units are source pixels unless a field says otherwise. A ``BBox`` is half-open in
the usual image sense: ``x2``/``y2`` are exclusive when slicing.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class BBox:
    x1: int
    y1: int
    x2: int
    y2: int

    @property
    def width(self) -> int:
        return max(1, self.x2 - self.x1)

    @property
    def height(self) -> int:
        return max(1, self.y2 - self.y1)

    @classmethod
    def from_norm(cls, values: list[float], width: int, height: int) -> "BBox":
        x1, y1, x2, y2 = (float(v) for v in values)
        return cls(
            x1=max(0, int(round(x1 * width))),
            y1=max(0, int(round(y1 * height))),
            x2=min(width, int(round(x2 * width))),
            y2=min(height, int(round(y2 * height))),
        )

    def padded(self, px: int, width: int, height: int) -> "BBox":
        return BBox(
            max(0, self.x1 - px),
            max(0, self.y1 - px),
            min(width, self.x2 + px),
            min(height, self.y2 + px),
        )

    def to_list(self) -> list[int]:
        return [self.x1, self.y1, self.x2, self.y2]


@dataclass
class TextRegion:
    """One piece of lettering, from reading to re-typesetting."""

    id: str
    source_text: str
    translation_ar: str
    style: str
    font_style: str
    bbox: BBox
    mask_path: str | None = None
    # The area the text may occupy: the mask's bounds (bubble, caption bar) when the
    # mask is a real container, otherwise the reading box.
    container: "BBox | None" = None
    aligned_text: str | None = None
    font_family: str = "kufi"
    font_size: int = 0
    color: tuple[int, int, int] = (20, 17, 15)
    lines: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "source_text": self.source_text,
            "translation_ar": self.translation_ar,
            "style": self.style,
            "font_style": self.font_style,
            "bbox": self.bbox.to_list(),
            "container": self.container.to_list() if self.container else None,
            "mask_path": self.mask_path,
            "font_family": self.font_family,
            "font_size": self.font_size,
            "color": list(self.color),
            "lines": self.lines,
        }


@dataclass
class Layout:
    """A fitted set of lines for one region."""

    lines: list[str]
    size: int
    line_height: int
    width: int
    height: int
    overflow: bool = False


@dataclass
class StageReport:
    name: str
    ms: int
    cost_usd: float
    detail: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "ms": self.ms, "cost_usd": round(self.cost_usd, 6), **self.detail}


@dataclass
class PageJob:
    id: str
    register: str
    width: int
    height: int
    artifacts: dict[str, str] = field(default_factory=dict)
    stages: list[StageReport] = field(default_factory=list)
    regions: list[TextRegion] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    total_cost_usd: float = 0.0

    def add_stage(self, name: str, ms: int, cost_usd: float, **detail: Any) -> StageReport:
        stage = StageReport(name=name, ms=ms, cost_usd=cost_usd, detail=detail)
        self.stages.append(stage)
        self.total_cost_usd += cost_usd
        return stage

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "register": self.register,
            "width": self.width,
            "height": self.height,
            "artifacts": self.artifacts,
            "stages": [s.to_dict() for s in self.stages],
            "regions": [r.to_dict() for r in self.regions],
            "warnings": self.warnings,
            "total_cost_usd": round(self.total_cost_usd, 6),
            "total_ms": sum(s.ms for s in self.stages),
        }
