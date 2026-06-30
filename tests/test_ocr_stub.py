import numpy as np

from src.ocr.factory import get_ocr_engine
from src.ocr.stub import StubOCREngine
from src.template.enums import OCREngine
from src.template.ocr_config import OCRConfig


def _config() -> OCRConfig:
    return OCRConfig(engine=OCREngine.PADDLE)


def test_stub_returns_default():
    engine = StubOCREngine()
    img = np.ones((10, 10, 3), dtype=np.uint8)
    result = engine.recognize(img, _config())
    assert result.raw_text == "SAMPLE"
    assert result.engine_name == "stub"


def test_stub_per_field_response():
    engine = StubOCREngine(responses={"pan_number": "ABCDE1234F"})
    img = np.ones((10, 10, 3), dtype=np.uint8)
    result = engine.recognize(img, _config(), field_id="pan_number")
    assert result.raw_text == "ABCDE1234F"


def test_stub_empty_image():
    engine = StubOCREngine()
    result = engine.recognize(np.zeros((0, 0), dtype=np.uint8), _config())
    assert result.raw_text == ""
    assert result.confidence == 0.0


def test_factory_returns_cached_stub():
    a = get_ocr_engine("stub")
    b = get_ocr_engine("stub")
    assert a is b
    assert isinstance(a, StubOCREngine)
