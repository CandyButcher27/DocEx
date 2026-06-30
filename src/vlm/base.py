from abc import ABC, abstractmethod

import numpy as np

from .schema import DerivedDocument


class VLMProvider(ABC):

    name: str = "base"

    @abstractmethod
    def derive_structure(self, images: list[np.ndarray], family_hint: str | None = None) -> DerivedDocument:
        ...
