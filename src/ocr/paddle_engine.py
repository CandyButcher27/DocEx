import time

import numpy as np

from src.models.ocr_result import OCRResult
from src.template.ocr_config import OCRConfig

from .base import OCREngineAdapter


class PaddleOCREngine(OCREngineAdapter):

    name = "paddle"

    def __init__(self, language: str = "en") -> None:
        from paddleocr import PaddleOCR

        self._ocr = PaddleOCR(use_angle_cls=True, lang=language, show_log=False)

    def recognize(self, image: np.ndarray, config: OCRConfig, field_id: str | None = None) -> OCRResult:
        if image is None or image.size == 0:
            return OCRResult(raw_text="", confidence=0.0, engine_name=self.name, processing_time_ms=0.0)

        start = time.perf_counter()
        result = self._ocr.ocr(image, cls=True)
        elapsed_ms = (time.perf_counter() - start) * 1000.0

        lines = result[0] if result and result[0] else []
        if not lines:
            return OCRResult(raw_text="", confidence=0.0, engine_name=self.name, processing_time_ms=elapsed_ms)

        texts = [line[1][0] for line in lines]
        confs = [float(line[1][1]) for line in lines]
        confidence = sum(confs) / len(confs)

        return OCRResult(
            raw_text=" ".join(texts).strip(),
            confidence=max(0.0, min(1.0, confidence)),
            engine_name=self.name,
            processing_time_ms=elapsed_ms,
        )
