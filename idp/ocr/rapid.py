from __future__ import annotations

import numpy as np

from ..models import BBox, OCRWord
from .base import OCREngine

_engine = None


def _get():
    global _engine
    if _engine is None:
        from rapidocr_onnxruntime import RapidOCR
        _engine = RapidOCR()
    return _engine


class RapidEngine(OCREngine):
    name = "rapidocr"

    def read(self, image: np.ndarray) -> list[OCRWord]:
        if image is None or image.size == 0:
            return []
        res, _ = _get()(image)
        words: list[OCRWord] = []
        for poly, text, conf in (res or []):
            xs = [p[0] for p in poly]
            ys = [p[1] for p in poly]
            bbox = BBox(int(min(xs)), int(min(ys)), int(max(xs)), int(max(ys)))
            words.append(OCRWord(text=text, bbox=bbox, conf=float(conf)))
        return words
