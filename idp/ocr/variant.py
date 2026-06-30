from __future__ import annotations

import cv2
import numpy as np

from ..models import OCRWord
from .base import OCREngine


def _binarize(image: np.ndarray) -> np.ndarray:
    g = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if image.ndim == 3 else image
    g = cv2.fastNlMeansDenoising(g, h=10)
    th = cv2.adaptiveThreshold(g, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                               cv2.THRESH_BINARY, 31, 11)
    return cv2.cvtColor(th, cv2.COLOR_GRAY2BGR)


class VariantEngine(OCREngine):
    """Genuine second voter: same backend, binarized + upscaled input."""

    def __init__(self, base: OCREngine, scale: float = 1.8):
        self.base = base
        self.scale = scale
        self.name = f"{base.name}+bin"

    def read(self, image: np.ndarray) -> list[OCRWord]:
        if image is None or image.size == 0:
            return []
        proc = _binarize(image)
        if self.scale != 1.0:
            proc = cv2.resize(proc, None, fx=self.scale, fy=self.scale,
                              interpolation=cv2.INTER_CUBIC)
        words = self.base.read(proc)
        if self.scale != 1.0:
            for w in words:
                w.bbox.x1 = int(w.bbox.x1 / self.scale)
                w.bbox.y1 = int(w.bbox.y1 / self.scale)
                w.bbox.x2 = int(w.bbox.x2 / self.scale)
                w.bbox.y2 = int(w.bbox.y2 / self.scale)
        return words
