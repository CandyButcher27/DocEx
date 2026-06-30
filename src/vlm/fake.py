import numpy as np

from .base import VLMProvider
from .schema import DerivedDocument, DerivedField, DerivedPage, DerivedSection


class FakeVLMProvider(VLMProvider):
    """Deterministic, offline VLM stand-in.

    Emits a fixed, plausible structure per page so the VLM-fallback path and
    auto-template generation can be exercised without any API key.
    """

    name = "fake"

    def __init__(self, document: DerivedDocument | None = None) -> None:
        self._document = document

    def derive_structure(self, images: list[np.ndarray], family_hint: str | None = None) -> DerivedDocument:
        if self._document is not None:
            return self._document

        pages = []
        for i, _ in enumerate(images, start=1):
            fields = [
                DerivedField(
                    id=f"page{i}_field_a",
                    label=f"Page {i} Field A",
                    datatype="text",
                    widget="textbox",
                    validator="text",
                    x=0.1,
                    y=0.1,
                    width=0.3,
                    height=0.05,
                ),
                DerivedField(
                    id=f"page{i}_field_b",
                    label=f"Page {i} Field B",
                    datatype="text",
                    widget="textbox",
                    validator="text",
                    x=0.1,
                    y=0.2,
                    width=0.3,
                    height=0.05,
                ),
            ]
            pages.append(DerivedPage(number=i, sections=[DerivedSection(id="derived", fields=fields)]))

        return DerivedDocument(
            family=family_hint or "auto_generated",
            issuer="Unknown",
            document_type="Auto-derived document",
            pages=pages,
        )
