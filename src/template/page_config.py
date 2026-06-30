from dataclasses import dataclass

from .section_config import SectionConfig


@dataclass(frozen=True, slots=True)
class PageConfig:

    number: int

    sections: list[SectionConfig]
