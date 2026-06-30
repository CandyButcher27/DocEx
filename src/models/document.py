from dataclasses import dataclass, field
from enum import Enum

from .field import Field
from .page import Page


class ExtractionRoute(Enum):
    TEMPLATE_MATCH = "template_match"
    VLM_FALLBACK = "vlm_fallback"


@dataclass(slots=True)
class Document:
    source_path: str
    template_id: str | None = None
    route: ExtractionRoute | None = None
    pages: list[Page] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.source_path:
            raise ValueError("source_path cannot be empty.")

        if not all(isinstance(p, Page) for p in self.pages):
            raise TypeError("All items in pages must be Page instances.")

    def all_fields(self) -> list[Field]:
        return [f for page in self.pages for f in page.fields]
