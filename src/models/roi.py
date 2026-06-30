from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ROI:
    x: float
    y: float
    width: float
    height: float

    def __post_init__(self) -> None:
        values = {
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
        }

        for name, value in values.items():
            if not 0.0 <= value <= 1.0:
                raise ValueError(
                    f"{name} must be between 0.0 and 1.0. Got {value}."
                )

        if self.x + self.width > 1.0:
            raise ValueError("ROI extends beyond the right edge of the page.")

        if self.y + self.height > 1.0:
            raise ValueError("ROI extends beyond the bottom edge of the page.")

    def to_pixels(
        self,
        image_width: int,
        image_height: int,
    ) -> tuple[int, int, int, int]:
        return (
            round(self.x * image_width),
            round(self.y * image_height),
            round(self.width * image_width),
            round(self.height * image_height),
        )

    @property
    def right(self) -> float:
        return self.x + self.width

    @property
    def bottom(self) -> float:
        return self.y + self.height
