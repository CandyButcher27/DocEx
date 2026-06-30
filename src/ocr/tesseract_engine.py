import time

import numpy as np

from src.models.ocr_result import OCRResult
from src.template.ocr_config import OCRConfig

from .base import OCREngineAdapter


class TesseractOCREngine(OCREngineAdapter):

    name = "tesseract"

    def __init__(self) -> None:
        import pytesseract

        self._pytesseract = pytesseract

    def recognize(self, image: np.ndarray, config: OCRConfig, field_id: str | None = None) -> OCRResult:
        if image is None or image.size == 0:
            return OCRResult(raw_text="", confidence=0.0, engine_name=self.name, processing_time_ms=0.0)

        lang = "eng" if config.language == "en" else config.language
        start = time.perf_counter()
        data = self._pytesseract.image_to_data(
            image, lang=lang, output_type=self._pytesseract.Output.DICT
        )
        elapsed_ms = (time.perf_counter() - start) * 1000.0

        words = [w for w in data["text"] if w.strip()]
        confs = [int(c) for c in data["conf"] if c not in ("-1", -1)]
        confidence = (sum(confs) / len(confs) / 100.0) if confs else 0.0

        return OCRResult(
            raw_text=" ".join(words).strip(),
            confidence=max(0.0, min(1.0, confidence)),
            engine_name=self.name,
            processing_time_ms=elapsed_ms,
        )
