import time

import numpy as np

from src.models.ocr_result import OCRResult
from src.template.ocr_config import OCRConfig

from .base import OCREngineAdapter

_PRINTED_MODEL = "microsoft/trocr-base-printed"
_HANDWRITTEN_MODEL = "microsoft/trocr-base-handwritten"


class TrOCREngine(OCREngineAdapter):

    name = "trocr"

    def __init__(self, handwritten: bool = True) -> None:
        from PIL import Image
        from transformers import TrOCRProcessor, VisionEncoderDecoderModel

        self._Image = Image
        model_name = _HANDWRITTEN_MODEL if handwritten else _PRINTED_MODEL
        self._processor = TrOCRProcessor.from_pretrained(model_name)
        self._model = VisionEncoderDecoderModel.from_pretrained(model_name)

    def recognize(self, image: np.ndarray, config: OCRConfig, field_id: str | None = None) -> OCRResult:
        if image is None or image.size == 0:
            return OCRResult(raw_text="", confidence=0.0, engine_name=self.name, processing_time_ms=0.0)

        pil_image = self._Image.fromarray(image).convert("RGB")
        start = time.perf_counter()
        pixel_values = self._processor(images=pil_image, return_tensors="pt").pixel_values
        generated_ids = self._model.generate(pixel_values)
        text = self._processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
        elapsed_ms = (time.perf_counter() - start) * 1000.0

        return OCRResult(
            raw_text=text.strip(),
            confidence=0.9 if text.strip() else 0.0,
            engine_name=self.name,
            processing_time_ms=elapsed_ms,
        )
