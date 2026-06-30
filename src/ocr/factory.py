from .base import OCREngineAdapter
from .stub import StubOCREngine

_CACHE: dict[str, OCREngineAdapter] = {}


def _build(name: str) -> OCREngineAdapter:
    if name == "stub":
        return StubOCREngine()
    if name == "tesseract":
        from .tesseract_engine import TesseractOCREngine

        return TesseractOCREngine()
    if name == "easyocr":
        from .easyocr_engine import EasyOCREngine

        return EasyOCREngine()
    if name == "trocr":
        from .trocr_engine import TrOCREngine

        return TrOCREngine()
    if name == "paddle":
        from .paddle_engine import PaddleOCREngine

        return PaddleOCREngine()

    raise ValueError(f"Unknown OCR engine '{name}'. Known: stub, tesseract, easyocr, trocr, paddle.")


def get_ocr_engine(name: str) -> OCREngineAdapter:
    key = name.strip().lower()
    if key not in _CACHE:
        _CACHE[key] = _build(key)
    return _CACHE[key]
