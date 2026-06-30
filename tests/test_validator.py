from src.models.ocr_result import OCRResult
from src.template.enums import ValidatorType
from src.template.validation_config import ValidationConfig
from src.validation.validator import validate_ocr


def _ocr(text: str) -> OCRResult:
    return OCRResult(raw_text=text, confidence=0.9, engine_name="stub", processing_time_ms=1.0)


def test_required_empty_is_invalid():
    result = validate_ocr(_ocr("   "), ValidationConfig(validator=ValidatorType.TEXT, required=True))
    assert result.is_valid is False
    assert result.validation_score == 0.0
    assert any("Required" in e for e in result.errors)


def test_optional_empty_is_valid():
    result = validate_ocr(_ocr(""), ValidationConfig(validator=ValidatorType.TEXT, required=False))
    assert result.is_valid is True
    assert result.normalized_text == ""


def test_valid_pan_scores_one():
    result = validate_ocr(_ocr("ABCDE1234F"), ValidationConfig(validator=ValidatorType.PAN))
    assert result.is_valid is True
    assert result.validation_score == 1.0
    assert result.normalized_text == "ABCDE1234F"
