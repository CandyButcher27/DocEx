from dataclasses import dataclass

from .page_config import PageConfig
from .preprocessing_config import PreprocessingConfig
from .registration_config import RegistrationConfig
from .template_metadata import TemplateMetadata


@dataclass(frozen=True, slots=True)
class Template:

    metadata: TemplateMetadata

    registration: RegistrationConfig

    preprocessing: PreprocessingConfig

    pages: list[PageConfig]