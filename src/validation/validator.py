from src.models.ocr_result import OCRResult
from src.models.validation_result import ValidationResult
from src.template.validation_config import ValidationConfig

from .validators import normalize_and_validate


def validate_ocr(ocr_result: OCRResult, config: ValidationConfig) -> ValidationResult:
    normalized, is_valid, errors = normalize_and_validate(ocr_result.raw_text, config.validator)

    if config.required and not normalized:
        is_valid = False
        errors = [*errors, "Required field is empty."]

    if not config.required and not normalized:
        is_valid = True
        errors = []

    score = 1.0 if is_valid else 0.0

    return ValidationResult(
        normalized_text=normalized,
        is_valid=is_valid,
        validation_score=score,
        errors=errors,
    )
