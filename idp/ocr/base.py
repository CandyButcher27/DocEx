from __future__ import annotations

from abc import ABC, abstractmethod

import numpy as np

from ..models import OCRWord


class OCREngine(ABC):
    name: str = "base"

    @abstractmethod
    def read(self, image: np.ndarray) -> list[OCRWord]:
        ...

    def read_text(self, image: np.ndarray) -> str:
        return " ".join(w.text for w in self.read(image))
