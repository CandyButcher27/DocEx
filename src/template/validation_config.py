from dataclasses import dataclass

from .enums import ValidatorType

@dataclass(frozen=True, slots=True)
class ValidationConfig:

    validator: ValidatorType

    required: bool = True
