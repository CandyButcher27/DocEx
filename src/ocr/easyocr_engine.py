import time

import numpy as np

from src.models.ocr_result import OCRResult
from src.template.ocr_config import OCRConfig

from .base import OCREngineAdapter


class EasyOCREngine(OCREngineAdapter):

    name = "easyocr"

    def __init__(self, languages: list[str] | None = None, gpu: bool = False) -> None:
        import easyocr

        self._reader = easyocr.Reader(languages or ["en"], gpu=gpu)

    def recognize(self, image: np.ndarray, config: OCRConfig, field_id: str | None = None) -> OCRResult:
        if image is None or image.size == 0:
            return OCRResult(raw_text="", confidence=0.0, engine_name=self.name, processing_time_ms=0.0)

        start = time.perf_counter()
        results = self._reader.readtext(image)
        elapsed_ms = (time.perf_counter() - start) * 1000.0

        if not results:
            return OCRResult(raw_text="", confidence=0.0, engine_name=self.name, processing_time_ms=elapsed_ms)

        texts = [r[1] for r in results]
        confs = [float(r[2]) for r in results]
        confidence = sum(confs) / len(confs)

        return OCRResult(
            raw_text=" ".join(texts).strip(),
            confidence=max(0.0, min(1.0, confidence)),
            engine_name=self.name,
            processing_time_ms=elapsed_ms,
        )
