from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

from src.models.document import ExtractionRoute
from src.template.registry import TemplateRegistry
from src.template.template import Template

from .matcher import MatchResult, match_images

REPO_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True, slots=True)
class RouteDecision:
    route: ExtractionRoute
    template: Template | None
    match_result: MatchResult | None


def annotated_fraction(template: Template) -> float:
    fields = [f for page in template.pages for section in page.sections for f in section.fields]
    if not fields:
        return 0.0
    annotated = sum(1 for f in fields if f.roi.x is not None)
    return annotated / len(fields)


def _load_reference_page(template: Template, page_number: int) -> np.ndarray | None:
    rel = template.registration.reference_images.get(page_number)
    if not rel:
        return None

    path = Path(rel)
    if not path.is_absolute():
        path = REPO_ROOT / path

    if not path.exists():
        return None

    return cv2.imread(str(path))


def route_document(
    page_images: list[np.ndarray],
    registry: TemplateRegistry,
    match_threshold: float,
    min_inliers: int,
    annotated_ratio: float = 0.5,
) -> RouteDecision:
    if not page_images:
        raise ValueError("page_images cannot be empty.")

    scanned_first_page = page_images[0]
    best_template: Template | None = None
    best_match: MatchResult | None = None

    for template in registry.all():
        reference = _load_reference_page(template, 1)
        if reference is None:
            continue

        result = match_images(scanned_first_page, reference, template.registration.method)

        if best_match is None or result.score > best_match.score:
            best_match = result
            best_template = template

    if (
        best_template is not None
        and best_match is not None
        and best_match.score >= match_threshold
        and best_match.num_inliers >= min_inliers
        and annotated_fraction(best_template) >= annotated_ratio
    ):
        return RouteDecision(
            route=ExtractionRoute.TEMPLATE_MATCH,
            template=best_template,
            match_result=best_match,
        )

    return RouteDecision(
        route=ExtractionRoute.VLM_FALLBACK,
        template=None,
        match_result=best_match,
    )
