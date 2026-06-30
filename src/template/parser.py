from collections import Counter

from .enums import ExportFormat, FieldType, FieldWidget, OCREngine, RegistrationMethod, ValidatorType
from .export_config import ExportConfig
from .field_config import FieldConfig
from .ocr_config import OCRConfig
from .page_config import PageConfig
from .preprocessing_config import PreprocessingConfig
from .registration_config import RegistrationConfig
from .roi_config import ROIConfig
from .section_config import SectionConfig
from .template import Template
from .template_metadata import TemplateMetadata
from .validation_config import ValidationConfig


class TemplateError(Exception):
    """Raised when a template YAML is malformed or fails validation on load."""


def _require(data: dict, key: str, context: str) -> object:
    if key not in data:
        raise TemplateError(f"{context}: missing required key '{key}'.")
    return data[key]


def parse_roi_config(data: dict | None) -> ROIConfig:
    if data is None:
        return ROIConfig(x=None, y=None, width=None, height=None)

    return ROIConfig(
        x=data.get("x"),
        y=data.get("y"),
        width=data.get("width"),
        height=data.get("height"),
    )


def parse_ocr_config(data: dict, context: str) -> OCRConfig:
    return OCRConfig(
        engine=OCREngine(_require(data, "engine", context)),
        language=data.get("language", "en"),
        handwritten=data.get("handwritten", True),
    )


def parse_validation_config(data: dict, context: str) -> ValidationConfig:
    return ValidationConfig(
        validator=ValidatorType(_require(data, "validator", context)),
        required=data.get("required", True),
    )


def parse_export_config(data: dict | None, field_id: str) -> ExportConfig:
    if data is None:
        return ExportConfig(key=field_id, format=ExportFormat.JSON)

    return ExportConfig(
        key=data.get("key", field_id),
        format=ExportFormat(data.get("format", "json")),
    )


def parse_field_config(data: dict) -> FieldConfig:
    field_id = _require(data, "id", "field")
    context = f"field '{field_id}'"

    return FieldConfig(
        id=field_id,
        label=_require(data, "label", context),
        datatype=FieldType(_require(data, "datatype", context)),
        widget=FieldWidget(_require(data, "widget", context)),
        roi=parse_roi_config(data.get("roi")),
        ocr=parse_ocr_config(_require(data, "ocr", context), context),
        validation=parse_validation_config(_require(data, "validation", context), context),
        export=parse_export_config(data.get("export"), field_id),
    )


def parse_section_config(data: dict) -> SectionConfig:
    section_id = _require(data, "id", "section")
    fields = [parse_field_config(f) for f in _require(data, "fields", f"section '{section_id}'")]

    return SectionConfig(
        id=section_id,
        fields=fields,
        repeatable=data.get("repeatable", False),
        max_items=data.get("max_items"),
    )


def parse_page_config(data: dict) -> PageConfig:
    page_number = _require(data, "page", "page")
    sections = [parse_section_config(s) for s in _require(data, "sections", f"page {page_number}")]

    return PageConfig(number=page_number, sections=sections)


def parse_registration_config(data: dict) -> RegistrationConfig:
    reference_images = data.get("reference_images", {})

    return RegistrationConfig(
        method=RegistrationMethod(_require(data, "method", "registration")),
        reference_images={int(k): v for k, v in reference_images.items()},
    )


def parse_preprocessing_config(data: dict) -> PreprocessingConfig:
    return PreprocessingConfig(
        deskew=data.get("deskew", True),
        perspective_correction=data.get("perspective_correction", True),
        adaptive_threshold=data.get("adaptive_threshold", True),
        denoise=data.get("denoise", True),
        contrast_enhancement=data.get("contrast_enhancement", True),
    )


def parse_template_metadata(data: dict, family: str, template_id: str, template_name: str, page_count: int) -> TemplateMetadata:
    metadata = data.get("metadata", {})

    return TemplateMetadata(
        family=family,
        template_id=template_id,
        template_name=template_name,
        variant=_require(metadata, "variant", "metadata"),
        version=_require(metadata, "version", "metadata"),
        page_count=page_count,
        issuer=_require(metadata, "issuer", "metadata"),
        document_type=_require(metadata, "document_type", "metadata"),
        description=metadata.get("description", ""),
    )


def _check_unique_field_ids(pages: list[PageConfig]) -> None:
    ids = [field.id for page in pages for section in page.sections for field in section.fields]
    duplicates = [field_id for field_id, count in Counter(ids).items() if count > 1]

    if duplicates:
        raise TemplateError(f"Duplicate field id(s) across template: {sorted(duplicates)}.")


def parse_template(data: dict, family: str) -> Template:
    template_id = _require(data, "id", "template")
    template_name = data.get("name", template_id)
    pages = [parse_page_config(p) for p in _require(data, "pages", "template")]

    _check_unique_field_ids(pages)

    metadata = parse_template_metadata(data, family, template_id, template_name, len(pages))
    registration = parse_registration_config(_require(data, "registration", "template"))
    preprocessing = parse_preprocessing_config(_require(data, "preprocessing", "template"))

    return Template(
        metadata=metadata,
        registration=registration,
        preprocessing=preprocessing,
        pages=pages,
    )
