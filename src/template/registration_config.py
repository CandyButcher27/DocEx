from dataclasses import dataclass

from .enums import RegistrationMethod

@dataclass(frozen=True, slots=True)
class RegistrationConfig:

    method: RegistrationMethod

    reference_images: dict[int, str]
