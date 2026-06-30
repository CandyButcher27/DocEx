from src.models.ocr_result import OCRResult
from src.models.validation_result import ValidationResult

OCR_WEIGHT = 0.5
VALIDATION_WEIGHT = 0.5


def compute_confidence(ocr_result: OCRResult, validation_result: ValidationResult) -> float:
    return OCR_WEIGHT * ocr_result.confidence + VALIDATION_WEIGHT * validation_result.validation_score
