from dataclasses import dataclass
from pathlib import Path

import numpy as np

from src.configs.settings import Settings, get_settings
from src.exporters.exporter import export_document
from src.models.document import Document, ExtractionRoute
from src.models.field import Field
from src.models.page import Page
from src.ocr.factory import get_ocr_engine
from src.preprocessing.cleaner import clean_image
from src.preprocessing.pdf_loader import pdf_to_images
from src.registration.aligner import align_to_reference
from src.registration.matcher import match_images
from src.registration.router import RouteDecision, route_document
from src.roi.cropper import crop_page_fields
from src.template.enums import ExportFormat
from src.template.loader import load_all_templates
from src.template.registry import TemplateRegistry
from src.template.template import Template
from src.validation.validator import validate_ocr
from src.vlm.factory import get_vlm_provider
from src.vlm.template_builder import save_generated_template


@dataclass(slots=True)
class PipelineResult:
    document: Document
    route: ExtractionRoute
    template_id: str
    export_path: Path | None
    match_score: float


def _align_or_raw(scanned: np.ndarray, template: Template, page_number: int) -> np.ndarray:
    from src.registration.router import _load_reference_page

    reference = _load_reference_page(template, page_number)
    if reference is None:
        return scanned

    try:
        result = match_images(scanned, reference, template.registration.method)
        if result.homography is not None and result.num_inliers >= 8:
            return align_to_reference(scanned, reference, result.homography)
    except Exception:
        pass

    return scanned


def _extract_with_template(
    template: Template,
    page_images: list[np.ndarray],
    ocr_engine_name: str,
) -> list[Page]:
    engine = get_ocr_engine(ocr_engine_name)
    pages: list[Page] = []

    field_configs = {
        field.id: field
        for tpl_page in template.pages
        for section in tpl_page.sections
        for field in section.fields
    }

    for tpl_page in template.pages:
        index = tpl_page.number - 1
        if index < 0 or index >= len(page_images):
            continue

        aligned = _align_or_raw(page_images[index], template, tpl_page.number)
        cleaned = clean_image(aligned, template.preprocessing)
        crops = crop_page_fields(cleaned, template, tpl_page.number)

        page_fields: list[Field] = []
        for field_id, crop in crops.items():
            config = field_configs[field_id]
            ocr_result = engine.recognize(crop, config.ocr, field_id)
            validation_result = validate_ocr(ocr_result, config.validation)
            page_fields.append(
                Field(config=config, ocr_result=ocr_result, validation_result=validation_result)
            )

        pages.append(Page(number=tpl_page.number, fields=page_fields))

    return pages


def extract_document(
    pdf_path: str | Path,
    settings: Settings | None = None,
    export_format: ExportFormat = ExportFormat.JSON,
    output_path: str | Path | None = None,
    page_images: list[np.ndarray] | None = None,
) -> PipelineResult:
    settings = settings or get_settings()

    if page_images is None:
        page_images = pdf_to_images(pdf_path, poppler_path=settings.poppler_path)

    if not page_images:
        raise ValueError(f"No pages rendered from {pdf_path}.")

    registry = load_all_templates(settings.templates_dir)
    decision: RouteDecision = route_document(
        page_images,
        registry,
        settings.registration_match_threshold,
        settings.registration_min_inliers,
    )

    route = decision.route
    match_score = decision.match_result.score if decision.match_result else 0.0

    if route == ExtractionRoute.TEMPLATE_MATCH and decision.template is not None:
        template = decision.template
    else:
        route = ExtractionRoute.VLM_FALLBACK
        provider = get_vlm_provider(settings)
        derived = provider.derive_structure(page_images)
        save_generated_template(derived, page_images, settings.templates_dir, settings.ocr_engine)
        registry = load_all_templates(settings.templates_dir)
        template = registry.get(f"{_slug(derived.family)}_auto")

    pages = _extract_with_template(template, page_images, settings.ocr_engine)
    document = Document(
        source_path=str(pdf_path),
        template_id=template.metadata.template_id,
        route=route,
        pages=pages,
    )

    export_path = None
    if output_path is not None:
        export_path = export_document(document, export_format, output_path)

    return PipelineResult(
        document=document,
        route=route,
        template_id=template.metadata.template_id,
        export_path=export_path,
        match_score=match_score,
    )


def _slug(text: str) -> str:
    from src.vlm.template_builder import _slug as slug

    return slug(text)
