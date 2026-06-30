from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class OCRResult:
    raw_text: str
    confidence: float
    engine_name: str
    processing_time_ms: float

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(
                f"Confidence must be between 0.0 and 1.0. Got {self.confidence}."
            )

        if self.processing_time_ms < 0:
            raise ValueError("Processing time cannot be negative.")

        if not self.engine_name:
            raise ValueError("Engine name cannot be empty.")
