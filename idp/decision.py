from __future__ import annotations

from collections import defaultdict
from typing import Optional

import numpy as np

from .config import ACCEPT_CONFIDENCE, REVIEW_CONFIDENCE
from .models import BBox, FieldDecision, FieldSpec, OCRCandidate
from .textutil import normalize
from .validate import validate_field


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
    def decide(self, spec: FieldSpec, candidates: list[OCRCandidate],
               vlm_cand: Optional[OCRCandidate], crop, roi: BBox | None) -> FieldDecision:
        all_c = list(candidates)
        if vlm_cand and vlm_cand.text.strip():
            all_c = all_c + [vlm_cand]

        if not all_c:
            return FieldDecision(
                name=spec.name, value="", confidence=0.0, source="pending_human",
                validated=False, status="review", candidates=[], roi=roi,
                note="no OCR/VLM signal in region")

        # VLM is authoritative for handwriting: if it produced a validating value, trust it.
        if vlm_cand and vlm_cand.text.strip():
            v_ok, v_clean, v_note = validate_field(spec, vlm_cand.text)
            if v_ok and v_clean:
                agrees = any(normalize(c.text) == normalize(vlm_cand.text) for c in candidates)
                conf = min(0.99, vlm_cand.conf + (0.1 if agrees else 0.0))
                conf = max(conf, ACCEPT_CONFIDENCE if agrees else conf)
                return FieldDecision(
                    name=spec.name, value=v_clean, confidence=conf, source="vlm",
                    validated=True,
                    status="accepted" if conf >= ACCEPT_CONFIDENCE else "review",
                    candidates=all_c, roi=roi,
                    note="ocr+vlm agree" if agrees else "vlm read")

        text, conf, agreement = _consensus(all_c)
        ok, cleaned, note = validate_field(spec, text)
        if ok and cleaned and agreement >= 0.5 and conf >= ACCEPT_CONFIDENCE:
            return FieldDecision(
                name=spec.name, value=cleaned, confidence=conf, source="ocr",
                validated=True, status="accepted", candidates=all_c, roi=roi, note=note)

        best_guess = cleaned or (vlm_cand.text if vlm_cand else "") or text
        return FieldDecision(
            name=spec.name, value=best_guess, confidence=conf,
            source="pending_human", validated=False, status="review",
            candidates=all_c, roi=roi, note=note or "low confidence / disagreement")
