import numpy as np

from src.models.ocr_result import OCRResult
from src.template.ocr_config import OCRConfig

from .base import OCREngineAdapter


class StubOCREngine(OCREngineAdapter):

    name = "stub"

    def __init__(self, responses: dict[str, str] | None = None, default_text: str = "SAMPLE") -> None:
        self._responses = responses or {}
        self._default_text = default_text

    def recognize(self, image: np.ndarray, config: OCRConfig, field_id: str | None = None) -> OCRResult:
        if image is None or getattr(image, "size", 0) == 0:
            return OCRResult(raw_text="", confidence=0.0, engine_name=self.name, processing_time_ms=0.0)

        text = self._responses.get(field_id, self._default_text) if field_id else self._default_text

        return OCRResult(
            raw_text=text,
            confidence=0.95,
            engine_name=self.name,
            processing_time_ms=0.0,
        )
