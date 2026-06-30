from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TemplateMetadata:
    """
    Stores metadata describing a template.
    """

    family: str
    template_id: str
    template_name: str
    variant: str
    version: str
    page_count: int
    issuer: str
    document_type: str
    description: str = ""

    def __post_init__(self) -> None:

        if not self.family.strip():
            raise ValueError("family cannot be empty.")

        if not self.template_id.strip():
            raise ValueError("template_id cannot be empty.")

        if not self.template_name.strip():
            raise ValueError("template_name cannot be empty.")

        if not self.variant.strip():
            raise ValueError("variant cannot be empty.")

        if not self.version.strip():
            raise ValueError("version cannot be empty.")

        if not self.issuer.strip():
            raise ValueError("issuer cannot be empty.")

        if not self.document_type.strip():
            raise ValueError("document_type cannot be empty.")

        if self.page_count <= 0:
            raise ValueError("page_count must be greater than zero.")