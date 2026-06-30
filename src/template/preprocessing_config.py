from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PreprocessingConfig:

    deskew: bool

    perspective_correction: bool

    adaptive_threshold: bool

    denoise: bool

    contrast_enhancement: bool