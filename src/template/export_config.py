from dataclasses import dataclass

from .enums import ExportFormat

@dataclass(frozen=True, slots=True)
class ExportConfig:

    key: str
    format: ExportFormat = ExportFormat.JSON
