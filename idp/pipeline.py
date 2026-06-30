from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np

from .classify import ClassifyResult, classify
from .config import OUTPUT_DIR
from .decision import DecisionEngine
from .models import FieldDecision, Template
from .ocr import OCREnsemble
from .render import load_first_page
from .review import build_review_queue
from .roi import crop, find_anchor, value_region
from .store import load_templates, save_template
from .textutil import normalize
from .vlm import StubVLM


@dataclass
class ExtractionResult:
    document: str
    template_id: str | None
    classification: dict
    fields: dict
    review_queue: list
    metadata: dict
    decisions: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "document": self.document,
            "template_id": self.template_id,
            "classification": self.classification,
            "fields": {k: v for k, v in self.fields.items()},
            "review_queue": self.review_queue,
            "metadata": self.metadata,
        }


class Pipeline:
    def __init__(self, templates: list[Template] | None = None,
                 ocr: OCREnsemble | None = None):
        self.ocr = ocr or OCREnsemble()
        self.vlm = StubVLM()
        self.engine = DecisionEngine(self.vlm)
        self.templates = templates if templates is not None else load_templates()

    def extract(self, doc_path: str | Path, save: bool = True) -> ExtractionResult:
        t0 = time.time()
        doc_path = Path(doc_path)
        image = load_first_page(doc_path)
        page_h, page_w = image.shape[:2]

        words = self.ocr.read_page(image)
        page_text = " ".join(w.text for w in words)

        cls: ClassifyResult = classify(image, page_text, self.templates)
        template = cls.template

        run_dir = OUTPUT_DIR / doc_path.stem
        crops_dir = run_dir / "crops"
        crops_dir.mkdir(parents=True, exist_ok=True)

        if template is None:
            learned = self.vlm.learn_template(image, page_text)
            learned.template_id = f"vlm_{doc_path.stem}"
            save_template(learned)
            return self._finalize(doc_path, None, cls, [], image, run_dir, t0,
                                  note="unknown template -> VLM stub learned new template (no fields)")

        decisions = self._extract_fields(template, words, image, page_w, page_h, crops_dir)
        return self._finalize(doc_path, template, cls, decisions, image, run_dir, t0)

    def _extract_fields(self, template, words, image, page_w, page_h, crops_dir):
        decisions: list[FieldDecision] = []
        for spec in template.fields:
            other_norms = {normalize(a) for f in template.fields if f.name != spec.name
                           for a in f.anchors}
            hit = find_anchor(words, spec.anchors)
            if hit is None:
                decisions.append(FieldDecision(
                    name=spec.name, value="", confidence=0.0, source="pending_human",
                    validated=False, status="review", note="anchor not found"))
                continue
            region, page_vals = value_region(hit, words, spec, page_w, page_h, other_norms)
            roi_crop = crop(image, region)
            candidates = self.ocr.read_roi(roi_crop)
            if page_vals:
                joined = " ".join(w.text for w in sorted(page_vals, key=lambda w: w.bbox.x1))
                import numpy as _np
                conf = float(_np.mean([w.conf for w in page_vals]))
                from .models import OCRCandidate
                candidates.append(OCRCandidate(joined, conf, "page"))

            dec = self.engine.decide(spec, candidates, roi_crop, region)
            crop_path = crops_dir / f"{normalize(spec.name)}.png"
            if roi_crop.size > 3:
                cv2.imwrite(str(crop_path), roi_crop)
                dec.crop_path = str(crop_path.relative_to(crops_dir.parent.parent))
            decisions.append(dec)
        return decisions

    def _finalize(self, doc_path, template, cls, decisions, image, run_dir, t0, note=""):
        fields = {d.name: d.to_public() for d in decisions}
        review = build_review_queue(decisions)
        accepted = sum(1 for d in decisions if d.status == "accepted")
        meta = {
            "pages_processed": 1,
            "engines": [e.name for e in self.ocr.engines],
            "fields_total": len(decisions),
            "fields_accepted": accepted,
            "fields_for_review": len(decisions) - accepted,
            "classification_method": cls.method,
            "classification_score": round(cls.score, 3),
            "elapsed_sec": round(time.time() - t0, 1),
        }
        if note:
            meta["note"] = note
        result = ExtractionResult(
            document=str(doc_path.name),
            template_id=template.template_id if template else None,
            classification={"method": cls.method, "score": round(cls.score, 3),
                            "scores": cls.scores},
            fields=fields, review_queue=review, metadata=meta, decisions=decisions)

        run_dir.mkdir(parents=True, exist_ok=True)
        out_json = run_dir / "result.json"
        out_json.write_text(json.dumps(result.to_dict(), indent=2), encoding="utf-8")
        result.metadata["output"] = str(out_json)
        return result
