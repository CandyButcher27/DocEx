from dataclasses import dataclass

from .enums import OCREngine

@dataclass(frozen=True, slots=True)
class OCRConfig:

    engine: OCREngine

    language: str = "en"

    handwritten: bool = True
