from __future__ import annotations

import numpy as np

from ..models import BBox, OCRWord
from .base import OCREngine


def available() -> bool:
    try:
        import pytesseract
        pytesseract.get_tesseract_version()
        return True
    except Exception:
        return False


class TesseractEngine(OCREngine):
    name = "tesseract"

    def read(self, image: np.ndarray) -> list[OCRWord]:
        import pytesseract
        from pytesseract import Output

        if image is None or image.size == 0:
            return []
        data = pytesseract.image_to_data(image, output_type=Output.DICT)
        words: list[OCRWord] = []
        for i, text in enumerate(data["text"]):
            text = text.strip()
            if not text:
                continue
            conf = float(data["conf"][i])
            if conf < 0:
                continue
            x, y, w, h = data["left"][i], data["top"][i], data["width"][i], data["height"][i]
            words.append(OCRWord(text, BBox(x, y, x + w, y + h), conf / 100.0))
        return words
