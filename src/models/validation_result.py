from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class ValidationResult:
    normalized_text: str
    is_valid: bool
    validation_score: float
    errors: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not isinstance(self.normalized_text, str):
            raise TypeError("normalized_text must be a string.")

        if not (0.0 <= self.validation_score <= 1.0):
            raise ValueError("validation_score must be between 0.0 and 1.0.")

        if not isinstance(self.errors, list):
            raise TypeError("errors must be a list of strings.")

        if not all(isinstance(error, str) for error in self.errors):
            raise TypeError("All items in errors must be strings.")

        if not isinstance(self.is_valid, bool):
            raise TypeError("is_valid must be a boolean.")
