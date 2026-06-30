import pytest

from src.template.enums import ValidatorType
from src.validation.validators import normalize_and_validate


@pytest.mark.parametrize(
    "text,validator,expected_norm,expected_valid",
    [
        ("ABCDE1234F", ValidatorType.PAN, "ABCDE1234F", True),
        ("abcde1234f", ValidatorType.PAN, "ABCDE1234F", True),
        ("ABCD1234F", ValidatorType.PAN, "ABCD1234F", False),
        ("john@example.com", ValidatorType.EMAIL, "john@example.com", True),
        ("not-an-email", ValidatorType.EMAIL, "not-an-email", False),
        ("9876543210", ValidatorType.PHONE, "9876543210", True),
        ("12345", ValidatorType.PHONE, "12345", False),
        ("SBIN0001234", ValidatorType.IFSC, "SBIN0001234", True),
        ("SBIN1001234", ValidatorType.IFSC, "SBIN1001234", False),
        ("560001", ValidatorType.PINCODE, "560001", True),
        ("12", ValidatorType.PINCODE, "12", False),
        ("Rs. 1,50,000", ValidatorType.AMOUNT, "150000", True),
        ("01/05/2024", ValidatorType.DATE, "2024-05-01", True),
        ("notadate", ValidatorType.DATE, "notadate", False),
        ("123456789012", ValidatorType.ACCOUNT_NUMBER, "123456789012", True),
        ("42.5", ValidatorType.NUMBER, "42.5", True),
        ("hello world", ValidatorType.TEXT, "hello world", True),
    ],
)
def test_normalize_and_validate(text, validator, expected_norm, expected_valid):
    norm, valid, _ = normalize_and_validate(text, validator)
    assert norm == expected_norm
    assert valid is expected_valid
