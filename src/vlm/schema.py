from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class DerivedField:
    id: str
    label: str
    datatype: str
    widget: str
    validator: str
    x: float
    y: float
    width: float
    height: float


@dataclass(frozen=True, slots=True)
class DerivedSection:
    id: str
    fields: list[DerivedField]


@dataclass(frozen=True, slots=True)
class DerivedPage:
    number: int
    sections: list[DerivedSection]


@dataclass(frozen=True, slots=True)
class DerivedDocument:
    family: str
    issuer: str
    document_type: str
    pages: list[DerivedPage] = field(default_factory=list)
