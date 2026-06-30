from __future__ import annotations

import numpy as np

from .models import FieldSpec, Template
from .ocr import OCREnsemble
from .phash import dhash


def build_template(template_id: str, name: str, reference_image: np.ndarray,
                   fields: list[FieldSpec], signature_phrases: list[str] | None = None,
                   ocr: OCREnsemble | None = None, source: str = "manual") -> Template:
    phrases = list(dict.fromkeys(signature_phrases or []))
    if not phrases:
        ocr = ocr or OCREnsemble()
        words = ocr.read_page(reference_image)
        auto = [w.text.strip() for w in words if len(w.text.strip()) >= 6 and w.conf >= 0.85]
        phrases = list(dict.fromkeys(auto[:10]))
    return Template(
        template_id=template_id,
        name=name,
        signature_phrases=phrases,
        fields=fields,
        phash=dhash(reference_image),
        source=source,
    )
