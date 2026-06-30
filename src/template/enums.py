from enum import Enum


class FieldType(Enum):
    """Supported data types that can be extracted from a document."""

    TEXT = "text"
    NUMBER = "number"
    DATE = "date"
    PAN = "pan"
    EMAIL = "email"
    PHONE = "phone"
    ADDRESS = "address"
    CHECKBOX = "checkbox"
    RADIO = "radio"
    SIGNATURE = "signature"
    IMAGE = "image"


class OCREngine(Enum):
    """Supported OCR engines."""

    PADDLE = "paddle"
    TROCR = "trocr"
    TESSERACT = "tesseract"
    EASYOCR = "easyocr"


class ValidatorType(Enum):
    """Supported validators."""

    TEXT = "text"
    NUMBER = "number"
    DATE = "date"
    PAN = "pan"
    EMAIL = "email"
    PHONE = "phone"
    AMOUNT = "amount"
    PINCODE = "pincode"
    IFSC = "ifsc"
    ACCOUNT_NUMBER = "account_number"
    NONE = "none"


class RegistrationMethod(Enum):
    """Supported document registration methods."""

    ORB = "orb"
    SIFT = "sift"
    AKAZE = "akaze"
    MANUAL = "manual"


class ExportFormat(Enum):
    """Supported export formats."""

    JSON = "json"
    CSV = "csv"
    
class FieldWidget(Enum):
    """Represents how a field appears on the document."""

    TEXTBOX = "textbox"
    CHECKBOX = "checkbox"
    RADIO = "radio"
    DROPDOWN = "dropdown"
    SIGNATURE = "signature"
    IMAGE = "image"
    TABLE = "table"