from abc import ABC, abstractmethod

import numpy as np

from src.models.ocr_result import OCRResult
from src.template.ocr_config import OCRConfig


class OCREngineAdapter(ABC):

    name: str = "base"

    @abstractmethod
    def recognize(self, image: np.ndarray, config: OCRConfig, field_id: str | None = None) -> OCRResult:
        ...
