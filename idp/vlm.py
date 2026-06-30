from __future__ import annotations

import numpy as np

from .models import FieldSpec, OCRCandidate, Template
from .validate import validate_field


class StubVLM:
    """Placeholder for a local Vision-Language Model.

    Real implementation: load a local VLM (e.g. Qw2-VL / MiniCPM-V) and prompt it
    with the cropped ROI + field name. This stub keeps the pipeline contract intact
    and is the ONLY simulated component. It does not call any network.
    """

    name = "vlm_stub"

    def arbitrate(self, crop: np.ndarray, spec: FieldSpec,
                  candidates: list[OCRCandidate]) -> tuple[str, float]:
        valid = []
        for c in candidates:
            ok, cleaned, _ = validate_field(spec, c.text)
            if ok and cleaned:
                valid.append((cleaned, c.conf))
        if valid:
            valid.sort(key=lambda x: x[1], reverse=True)
            text, conf = valid[0]
            return text, min(0.75, 0.55 + conf * 0.2)
        if candidates:
            best = max(candidates, key=lambda c: c.conf)
            return best.text, min(0.6, best.conf)
        return "", 0.0

    def learn_template(self, image: np.ndarray, page_text: str) -> Template:
        # Stub: a real VLM would derive layout + fields from the image here.
        from .textutil import normalize_tokens
        toks = normalize_tokens(page_text)
        sig = list(dict.fromkeys(toks))[:8]
        return Template(
            template_id="vlm_generated",
            name="VLM-generated (stub)",
            signature_phrases=sig,
            fields=[],
            source="vlm_stub",
        )
