from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np

from .config import CLASSIFY_TEXT_THRESHOLD, PHASH_MAX_DISTANCE
from .models import Template
from .phash import dhash, hamming
from .textutil import contains_ratio


@dataclass
class ClassifyResult:
    template: Optional[Template]
    score: float
    method: str          # phash | text | none
    scores: dict


def _text_coverage(template: Template, page_text: str) -> float:
    phrases = template.signature_phrases
    if not phrases:
        return 0.0
    hits = sum(1 for p in phrases if contains_ratio(p, page_text) >= 0.72)
    return hits / len(phrases)


def classify(image: np.ndarray, page_text: str, templates: list[Template]) -> ClassifyResult:
    scores: dict = {}
    if not templates:
        return ClassifyResult(None, 0.0, "none", scores)

    page_hash = dhash(image)
    best_t, best_text = None, -1.0
    best_phash_t, best_phash_d = None, 10 ** 6

    for t in templates:
        cov = _text_coverage(t, page_text)
        d = hamming(t.phash, page_hash) if t.phash else 10 ** 6
        scores[t.template_id] = {"text_coverage": round(cov, 3), "phash_distance": d}
        if cov > best_text:
            best_text, best_t = cov, t
        if d < best_phash_d:
            best_phash_d, best_phash_t = d, t

    if best_phash_d <= PHASH_MAX_DISTANCE:
        return ClassifyResult(best_phash_t, 1.0 - best_phash_d / 256.0, "phash", scores)
    if best_text >= CLASSIFY_TEXT_THRESHOLD:
        return ClassifyResult(best_t, best_text, "text", scores)
    return ClassifyResult(None, best_text, "none", scores)
