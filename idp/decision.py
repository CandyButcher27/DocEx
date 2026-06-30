from __future__ import annotations

from collections import defaultdict

import numpy as np

from .config import ACCEPT_CONFIDENCE, REVIEW_CONFIDENCE
from .models import BBox, FieldDecision, FieldSpec, OCRCandidate
from .textutil import normalize
from .validate import validate_field
from .vlm import StubVLM


def _consensus(candidates: list[OCRCandidate]) -> tuple[str, float, float]:
    groups: dict[str, list[OCRCandidate]] = defaultdict(list)
    for c in candidates:
        if c.text.strip():
            groups[normalize(c.text)].append(c)
    if not groups:
        return "", 0.0, 0.0
    best_norm = max(groups, key=lambda k: (sum(c.conf for c in groups[k]), len(groups[k])))
    grp = groups[best_norm]
    rep = max(grp, key=lambda c: c.conf)
    agreement = len(grp) / len(candidates)
    conf = float(np.mean([c.conf for c in grp]))
    return rep.text, conf, agreement


class DecisionEngine:
    def __init__(self, vlm: StubVLM | None = None):
        self.vlm = vlm or StubVLM()

    def decide(self, spec: FieldSpec, candidates: list[OCRCandidate],
               crop, roi: BBox | None) -> FieldDecision:
        if not candidates:
            return FieldDecision(
                name=spec.name, value="", confidence=0.0, source="pending_human",
                validated=False, status="review", candidates=[], roi=roi,
                note="no OCR signal in region")

        text, conf, agreement = _consensus(candidates)
        ok, cleaned, note = validate_field(spec, text)

        strong = agreement >= 0.5 and conf >= ACCEPT_CONFIDENCE
        if ok and cleaned and strong:
            return FieldDecision(
                name=spec.name, value=cleaned, confidence=conf, source="ocr",
                validated=True, status="accepted", candidates=candidates, roi=roi,
                note=note)

        # arbitration
        v_text, v_conf = self.vlm.arbitrate(crop, spec, candidates)
        v_ok, v_clean, v_note = validate_field(spec, v_text)
        if v_ok and v_clean and v_conf >= REVIEW_CONFIDENCE and (v_conf >= ACCEPT_CONFIDENCE or ok):
            final_conf = max(v_conf, conf if ok else 0.0)
            return FieldDecision(
                name=spec.name, value=v_clean, confidence=final_conf, source="vlm_stub",
                validated=v_ok, status="accepted" if final_conf >= ACCEPT_CONFIDENCE else "review",
                candidates=candidates, roi=roi, note=v_note or note)

        best_guess = v_clean or cleaned or text
        return FieldDecision(
            name=spec.name, value=best_guess, confidence=max(conf, v_conf),
            source="pending_human", validated=False, status="review",
            candidates=candidates, roi=roi,
            note=note or v_note or "low confidence / disagreement")
