from dataclasses import dataclass, field

from .field import Field


@dataclass(slots=True)
class Page:
    number: int
    fields: list[Field] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.number <= 0:
            raise ValueError("Page number must be greater than zero.")

        if not all(isinstance(f, Field) for f in self.fields):
            raise TypeError("All items in fields must be Field instances.")

    def field_by_id(self, field_id: str) -> Field | None:
        return next((f for f in self.fields if f.config.id == field_id), None)
