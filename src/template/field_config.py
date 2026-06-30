from dataclasses import dataclass

from .enums import FieldType
from .export_config import ExportConfig
from .ocr_config import OCRConfig
from .roi_config import ROIConfig
from .validation_config import ValidationConfig


@dataclass(frozen=True, slots=True)
class FieldConfig:

    id: str

    label: str

    datatype: FieldType

    roi: ROIConfig

    ocr: OCRConfig

    validation: ValidationConfig

    export: ExportConfig
