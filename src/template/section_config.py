from dataclasses import dataclass

from .field_config import FieldConfig


@dataclass(frozen=True, slots=True)
class SectionConfig:

    name: str

    fields: list[FieldConfig]
