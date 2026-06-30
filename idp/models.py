from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class BBox:
    x1: int
    y1: int
    x2: int
    y2: int

    @property
    def w(self) -> int:
        return self.x2 - self.x1

    @property
    def h(self) -> int:
        return self.y2 - self.y1

    @property
    def cx(self) -> float:
        return (self.x1 + self.x2) / 2

    @property
    def cy(self) -> float:
        return (self.y1 + self.y2) / 2

    def as_list(self) -> list[int]:
        return [self.x1, self.y1, self.x2, self.y2]

    @staticmethod
    def from_list(v) -> "BBox":
        return BBox(int(v[0]), int(v[1]), int(v[2]), int(v[3]))


@dataclass
class OCRWord:
    text: str
    bbox: BBox
    conf: float


@dataclass
class FieldSpec:
    name: str
    anchors: list[str]
    value_region: str = "right"          # right | below | right_then_below
    datatype: str = "text"               # text | number | date | pan | choice
    regex: Optional[str] = None
    required: bool = False
    max_len: Optional[int] = None
    choices: Optional[list[str]] = None

    @staticmethod
    def from_dict(d: dict) -> "FieldSpec":
        return FieldSpec(
            name=d["name"],
            anchors=d.get("anchors", []),
            value_region=d.get("value_region", "right"),
            datatype=d.get("datatype", "text"),
            regex=d.get("regex"),
            required=d.get("required", False),
            max_len=d.get("max_len"),
            choices=d.get("choices"),
        )


@dataclass
class Template:
    template_id: str
    name: str
    signature_phrases: list[str]
    fields: list[FieldSpec]
    phash: Optional[str] = None
    source: str = "manual"               # manual | vlm_stub

    def to_dict(self) -> dict:
        return {
            "template_id": self.template_id,
            "name": self.name,
            "source": self.source,
            "phash": self.phash,
            "signature_phrases": self.signature_phrases,
            "fields": [asdict(f) for f in self.fields],
        }

    @staticmethod
    def from_dict(d: dict) -> "Template":
        return Template(
            template_id=d["template_id"],
            name=d["name"],
            signature_phrases=d.get("signature_phrases", []),
            fields=[FieldSpec.from_dict(f) for f in d.get("fields", [])],
            phash=d.get("phash"),
            source=d.get("source", "manual"),
        )


@dataclass
class OCRCandidate:
    text: str
    conf: float
    source: str          # engine name


@dataclass
class FieldDecision:
    name: str
    value: str
    confidence: float
    source: str          # ocr | vlm_stub | pending_human
    validated: bool
    status: str          # accepted | review
    candidates: list[OCRCandidate] = field(default_factory=list)
    roi: Optional[BBox] = None
    crop_path: Optional[str] = None
    note: str = ""

    def to_public(self) -> dict:
        out = {
            "value": self.value,
            "confidence": round(self.confidence, 3),
            "source": self.source,
            "validated": self.validated,
            "status": self.status,
        }
        if self.note:
            out["note"] = self.note
        return out
