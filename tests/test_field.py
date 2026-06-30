import unittest

from src.models.field import Field
from src.models.ocr_result import OCRResult
from src.models.validation_result import ValidationResult
from src.template.enums import ExportFormat, FieldType, OCREngine, ValidatorType
from src.template.export_config import ExportConfig
from src.template.field_config import FieldConfig
from src.template.ocr_config import OCRConfig
from src.template.roi_config import ROIConfig
from src.template.validation_config import ValidationConfig


class TestField(unittest.TestCase):

    def setUp(self):
        self.config = FieldConfig(
            id="pan_number",
            label="PAN Number",
            datatype=FieldType.PAN,
            roi=ROIConfig(
                x=0.1,
                y=0.2,
                width=0.3,
                height=0.1
            ),
            ocr=OCRConfig(
                engine=OCREngine.PADDLE
            ),
            validation=ValidationConfig(
                validator=ValidatorType.PAN
            ),
            export=ExportConfig(
                key="pan_number",
                format=ExportFormat.JSON
            )
        )

        self.other_config = FieldConfig(
            id="customer_name",
            label="Customer Name",
            datatype=FieldType.TEXT,
            roi=ROIConfig(
                x=0.4,
                y=0.2,
                width=0.2,
                height=0.1
            ),
            ocr=OCRConfig(
                engine=OCREngine.PADDLE
            ),
            validation=ValidationConfig(
                validator=ValidatorType.TEXT
            ),
            export=ExportConfig(
                key="customer_name",
                format=ExportFormat.JSON
            )
        )

        self.invalid_config = {
            "id": "invalid",
            "label": "Invalid",
            "datatype": "string",
        }

        self.ocr_result = OCRResult(
            raw_text="ABCDE1234F",
            confidence=0.98,
            engine_name="PaddleOCR",
            processing_time_ms=25.4
        )

        self.validation_result = ValidationResult(
            normalized_text="ABCDE1234F",
            is_valid=True,
            validation_score=1.0
        )

    def test_valid_field_creation(self):
        """Test creation of a valid Field."""

        field = Field(
            config=self.config
        )

        self.assertEqual(field.config, self.config)
        self.assertIsNone(field.ocr_result)
        self.assertIsNone(field.validation_result)

    def test_field_with_results(self):
        """Test Field populated with OCR and Validation results."""

        field = Field(
            config=self.config,
            ocr_result=self.ocr_result,
            validation_result=self.validation_result
        )

        self.assertEqual(field.config, self.config)
        self.assertEqual(field.ocr_result, self.ocr_result)
        self.assertEqual(field.validation_result, self.validation_result)

    def test_config_can_vary_per_field(self):
        """Field accepts different valid FieldConfig instances."""

        field = Field(
            config=self.other_config
        )

        self.assertEqual(field.config, self.other_config)

    def test_invalid_config(self):
        """Field config must be a FieldConfig instance."""

        with self.assertRaises(TypeError):
            Field(
                config=self.invalid_config
            )

    def test_invalid_ocr_result(self):
        """OCRResult must be an OCRResult instance or None."""

        with self.assertRaises(TypeError):
            Field(
                config=self.config,
                ocr_result="invalid"
            )

    def test_invalid_validation_result(self):
        """ValidationResult must be a ValidationResult instance or None."""

        with self.assertRaises(TypeError):
            Field(
                config=self.config,
                validation_result="invalid"
            )

    def test_attach_ocr_result(self):
        """OCRResult can be attached after creation."""

        field = Field(
            config=self.config
        )

        field.ocr_result = self.ocr_result

        self.assertEqual(field.ocr_result, self.ocr_result)

    def test_attach_validation_result(self):
        """ValidationResult can be attached after creation."""

        field = Field(
            config=self.config
        )

        field.validation_result = self.validation_result

        self.assertEqual(field.validation_result, self.validation_result)


if __name__ == "__main__":
    unittest.main()
