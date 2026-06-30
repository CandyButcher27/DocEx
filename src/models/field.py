from dataclasses import dataclass

from .ocr_result import OCRResult
from .validation_result import ValidationResult
from src.template.field_config import FieldConfig


@dataclass(slots=True)
class Field:
    config: FieldConfig
    ocr_result: OCRResult | None = None
    validation_result: ValidationResult | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.config, FieldConfig):
            raise TypeError("config must be an instance of FieldConfig.")

        if self.ocr_result is not None and not isinstance(self.ocr_result, OCRResult):
            raise TypeError(
                "ocr_result must be an instance of OCRResult or None."
            )

        if (
            self.validation_result is not None
            and not isinstance(self.validation_result, ValidationResult)
        ):
            raise TypeError(
                "validation_result must be an instance of ValidationResult or None."
            )
