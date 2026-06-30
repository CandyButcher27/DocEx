from __future__ import annotations

import re

import numpy as np

from ..models import OCRCandidate, OCRWord

_lead_marker = re.compile(r"^\s*\(?\d{1,2}[\).]\s*")


def _strip_markers(text: str) -> str:
    prev = None
    while prev != text:
        prev = text
        text = _lead_marker.sub("", text).strip()
    return text
from .base import OCREngine
from .rapid import RapidEngine
from .variant import VariantEngine
from . import tesseract as tess


def _join(words: list[OCRWord]) -> tuple[str, float]:
    words = sorted(words, key=lambda w: (w.bbox.cy, w.bbox.x1))
    text = " ".join(w.text for w in words).strip()
    conf = float(np.mean([w.conf for w in words])) if words else 0.0
    return text, conf


class OCREnsemble:
    def __init__(self, engines: list[OCREngine] | None = None):
        if engines is None:
            primary = RapidEngine()
            engines = [primary, VariantEngine(primary)]
            if tess.available():
                engines.append(tess.TesseractEngine())
        self.engines = engines
        self.primary = engines[0]

    def read_page(self, image: np.ndarray) -> list[OCRWord]:
        return self.primary.read(image)

    def read_roi(self, crop: np.ndarray) -> list[OCRCandidate]:
        cands: list[OCRCandidate] = []
        for eng in self.engines:
            try:
                text, conf = _join(eng.read(crop))
            except Exception:
                continue
            text = _strip_markers(text)
            if text:
                cands.append(OCRCandidate(text=text, conf=conf, source=eng.name))
        return cands
