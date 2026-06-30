import pytest

from src.models.ocr_result import OCRResult


def test_create_valid_ocr_result():
    """
    A valid OCRResult should be created successfully.
    """
    result = OCRResult(
        raw_text="ABCDE1234F",
        confidence=0.98,
        engine_name="PaddleOCR",
        processing_time_ms=12.5,
    )

    assert result.raw_text == "ABCDE1234F"
    assert result.confidence == 0.98
    assert result.engine_name == "PaddleOCR"
    assert result.processing_time_ms == 12.5


def test_confidence_zero_is_valid():
    """
    Confidence can be exactly 0.0.
    """
    result = OCRResult(
        raw_text="",
        confidence=0.0,
        engine_name="PaddleOCR",
        processing_time_ms=5.0,
    )

    assert result.confidence == 0.0


def test_confidence_one_is_valid():
    """
    Confidence can be exactly 1.0.
    """
    result = OCRResult(
        raw_text="ABCDE1234F",
        confidence=1.0,
        engine_name="PaddleOCR",
        processing_time_ms=5.0,
    )

    assert result.confidence == 1.0


def test_confidence_less_than_zero():
    """
    Confidence below 0 should raise ValueError.
    """
    with pytest.raises(ValueError):
        OCRResult(
            raw_text="ABC",
            confidence=-0.1,
            engine_name="PaddleOCR",
            processing_time_ms=10,
        )


def test_confidence_greater_than_one():
    """
    Confidence above 1 should raise ValueError.
    """
    with pytest.raises(ValueError):
        OCRResult(
            raw_text="ABC",
            confidence=1.1,
            engine_name="PaddleOCR",
            processing_time_ms=10,
        )


def test_negative_processing_time():
    """
    Processing time cannot be negative.
    """
    with pytest.raises(ValueError):
        OCRResult(
            raw_text="ABC",
            confidence=0.9,
            engine_name="PaddleOCR",
            processing_time_ms=-1,
        )


def test_empty_engine_name():
    """
    Engine name cannot be an empty string.
    """
    with pytest.raises(ValueError):
        OCRResult(
            raw_text="ABC",
            confidence=0.9,
            engine_name="",
            processing_time_ms=10,
        )


def test_whitespace_raw_text_is_allowed():
    """
    OCRResult should store exactly what the OCR engine returned.
    Cleaning is handled by the Validation module.
    """
    result = OCRResult(
        raw_text="  ABCDE1234F \n",
        confidence=0.95,
        engine_name="PaddleOCR",
        processing_time_ms=8,
    )

    assert result.raw_text == "  ABCDE1234F \n"


def test_result_is_immutable():
    """
    OCRResult should be immutable.
    """
    result = OCRResult(
        raw_text="ABCDE1234F",
        confidence=0.98,
        engine_name="PaddleOCR",
        processing_time_ms=5,
    )

    with pytest.raises(Exception):
        result.raw_text = "XYZ"