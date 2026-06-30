import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.models.validation_result import ValidationResult


class TestValidationResult(unittest.TestCase):

    def test_valid_validation_result(self):
        """Test creation of a valid ValidationResult."""

        result = ValidationResult(
            normalized_text="ABCDE1234F",
            is_valid=True,
            validation_score=1.0
        )

        self.assertEqual(result.normalized_text, "ABCDE1234F")
        self.assertTrue(result.is_valid)
        self.assertEqual(result.validation_score, 1.0)
        self.assertEqual(result.errors, [])

    def test_valid_validation_result_with_errors(self):
        """Test creation of an invalid ValidationResult."""

        errors = [
            "Regex validation failed.",
            "Invalid PAN format."
        ]

        result = ValidationResult(
            normalized_text="ABCDE123",
            is_valid=False,
            validation_score=0.4,
            errors=errors
        )

        self.assertFalse(result.is_valid)
        self.assertEqual(result.errors, errors)

    def test_validation_score_below_zero(self):
        """validation_score cannot be negative."""

        with self.assertRaises(ValueError):
            ValidationResult(
                normalized_text="ABC",
                is_valid=True,
                validation_score=-0.1
            )

    def test_validation_score_above_one(self):
        """validation_score cannot exceed 1."""

        with self.assertRaises(ValueError):
            ValidationResult(
                normalized_text="ABC",
                is_valid=True,
                validation_score=1.1
            )

    def test_normalized_text_must_be_string(self):
        """normalized_text must be a string."""

        with self.assertRaises(TypeError):
            ValidationResult(
                normalized_text=12345, # Not a string
                is_valid=True,
                validation_score=0.9
            )

    def test_is_valid_must_be_boolean(self):
        """is_valid must be a boolean."""

        with self.assertRaises(TypeError):
            ValidationResult(
                normalized_text="ABC",
                is_valid="yes", # Not a boolean
                validation_score=0.9
            )

    def test_errors_must_be_list(self):
        """errors must be a list."""

        with self.assertRaises(TypeError):
            ValidationResult(
                normalized_text="ABC",
                is_valid=False,
                validation_score=0.2,
                errors="Regex failed"  # Not a list
            )

    def test_errors_must_contain_strings(self):
        """Every error must be a string."""

        with self.assertRaises(TypeError):
            ValidationResult(
                normalized_text="ABC",
                is_valid=False,
                validation_score=0.2,
                errors=["Regex failed", 404]
            )

    def test_empty_normalized_text(self):
        """Empty strings are allowed."""

        result = ValidationResult(
            normalized_text="",
            is_valid=False,
            validation_score=0.0
        )

        self.assertEqual(result.normalized_text, "")
        self.assertFalse(result.is_valid)

    def test_default_errors_list_is_empty(self):
        """errors should default to an empty list."""

        result = ValidationResult(
            normalized_text="12345",
            is_valid=True,
            validation_score=1.0
        )

        self.assertEqual(result.errors, [])


if __name__ == "__main__":
    unittest.main()