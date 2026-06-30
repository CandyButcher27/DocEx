from dataclasses import dataclass

from .field_config import FieldConfig


@dataclass(frozen=True, slots=True)
class SectionConfig:

    id: str

    fields: list[FieldConfig]

    repeatable: bool = False

    max_items: int | None = None
