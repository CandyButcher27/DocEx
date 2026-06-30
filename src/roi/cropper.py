import numpy as np

from src.template.roi_config import ROIConfig
from src.template.template import Template


def crop_roi(image: np.ndarray, roi: ROIConfig) -> np.ndarray | None:
    if roi.x is None or roi.y is None or roi.width is None or roi.height is None:
        return None

    h, w = image.shape[:2]
    x0 = max(0, min(w, round(roi.x * w)))
    y0 = max(0, min(h, round(roi.y * h)))
    x1 = max(0, min(w, round((roi.x + roi.width) * w)))
    y1 = max(0, min(h, round((roi.y + roi.height) * h)))

    if x1 <= x0 or y1 <= y0:
        return None

    return image[y0:y1, x0:x1]


def crop_page_fields(image: np.ndarray, template: Template, page_number: int) -> dict[str, np.ndarray]:
    page = next((p for p in template.pages if p.number == page_number), None)
    if page is None:
        return {}

    crops: dict[str, np.ndarray] = {}
    for section in page.sections:
        for field in section.fields:
            crop = crop_roi(image, field.roi)
            if crop is not None:
                crops[field.id] = crop

    return crops
