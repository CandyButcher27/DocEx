from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ROIConfig:
    x: float | None
    y: float | None
    width: float | None
    height: float | None