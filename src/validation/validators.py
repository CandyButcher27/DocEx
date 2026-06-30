import re
from datetime import datetime

from src.template.enums import ValidatorType

_PAN_RE = re.compile(r"^[A-Z]{5}[0-9]{4}[A-Z]$")
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_IFSC_RE = re.compile(r"^[A-Z]{4}0[A-Z0-9]{6}$")
_PHONE_RE = re.compile(r"^[6-9][0-9]{9}$")
_PINCODE_RE = re.compile(r"^[1-9][0-9]{5}$")
_ACCOUNT_RE = re.compile(r"^[0-9]{9,18}$")
_DATE_FORMATS = ("%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y", "%Y-%m-%d", "%d/%m/%y")


def _clean(text: str) -> str:
    return " ".join(text.strip().split())


def _digits(text: str) -> str:
    return re.sub(r"[^0-9]", "", text)


def normalize_and_validate(text: str, validator: ValidatorType) -> tuple[str, bool, list[str]]:
    cleaned = _clean(text)

    if validator in (ValidatorType.NONE, ValidatorType.TEXT):
        return cleaned, True, []

    if validator == ValidatorType.NUMBER:
        normalized = re.sub(r"[^0-9.\-]", "", cleaned)
        if normalized and re.fullmatch(r"-?[0-9]*\.?[0-9]+", normalized):
            return normalized, True, []
        return cleaned, False, ["Not a valid number."]

    if validator == ValidatorType.AMOUNT:
        normalized = _digits(cleaned)
        if normalized:
            return normalized, True, []
        return cleaned, False, ["Not a valid amount."]

    if validator == ValidatorType.PAN:
        normalized = cleaned.upper().replace(" ", "")
        return (normalized, True, []) if _PAN_RE.match(normalized) else (normalized, False, ["Invalid PAN format."])

    if validator == ValidatorType.EMAIL:
        normalized = cleaned.lower().replace(" ", "")
        return (normalized, True, []) if _EMAIL_RE.match(normalized) else (normalized, False, ["Invalid email format."])

    if validator == ValidatorType.PHONE:
        normalized = _digits(cleaned)[-10:]
        return (normalized, True, []) if _PHONE_RE.match(normalized) else (normalized, False, ["Invalid phone number."])

    if validator == ValidatorType.PINCODE:
        normalized = _digits(cleaned)
        return (normalized, True, []) if _PINCODE_RE.match(normalized) else (normalized, False, ["Invalid pincode."])

    if validator == ValidatorType.IFSC:
        normalized = cleaned.upper().replace(" ", "")
        return (normalized, True, []) if _IFSC_RE.match(normalized) else (normalized, False, ["Invalid IFSC code."])

    if validator == ValidatorType.ACCOUNT_NUMBER:
        normalized = _digits(cleaned)
        return (normalized, True, []) if _ACCOUNT_RE.match(normalized) else (normalized, False, ["Invalid account number."])

    if validator == ValidatorType.DATE:
        normalized = cleaned.replace(" ", "")
        for fmt in _DATE_FORMATS:
            try:
                parsed = datetime.strptime(normalized, fmt)
                return parsed.strftime("%Y-%m-%d"), True, []
            except ValueError:
                continue
        return normalized, False, ["Invalid date format."]

    return cleaned, True, []
