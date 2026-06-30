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
from .models import OCRCandidate
from .review import build_review_queue
from .roi import crop, find_anchor, value_region
from .store import load_templates, save_template
from .textutil import normalize
from .vlm import VLMClient, get_vlm


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
                 ocr: OCREnsemble | None = None, vlm: VLMClient | None = None):
        self.ocr = ocr or OCREnsemble()
        self.vlm = vlm or get_vlm()
        self.engine = DecisionEngine()
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

        learned_note = ""
        if template is None:
            template = self.vlm.detect_format(image, page_text)
            template.template_id = f"vlm_{doc_path.stem}"
            save_template(template)
            learned_note = (f"unknown template -> VLM ({self.vlm.name}) derived "
                            f"{len(template.fields)} fields and cached a new template")
            if not template.fields:
                return self._finalize(doc_path, template, cls, [], image, run_dir, t0,
                                      note=learned_note + " (no fields detected)")

        vlm_values = {}
        try:
            vlm_values = self.vlm.extract_fields(image, template.fields)
        except Exception as e:
            learned_note = (learned_note + " | ").lstrip(" |") + f"vlm extract error: {e}"

        decisions = self._extract_fields(template, words, image, page_w, page_h,
                                         crops_dir, vlm_values)
        return self._finalize(doc_path, template, cls, decisions, image, run_dir, t0,
                              note=learned_note)

    def _extract_fields(self, template, words, image, page_w, page_h, crops_dir, vlm_values):
        decisions: list[FieldDecision] = []
        for spec in template.fields:
            vlm_cand = self._vlm_candidate(spec, vlm_values)
            other_norms = {normalize(a) for f in template.fields if f.name != spec.name
                           for a in f.anchors}
            hit = find_anchor(words, spec.anchors)
            region = None
            candidates: list[OCRCandidate] = []
            roi_crop = np.zeros((1, 1, 3), np.uint8)
            if hit is not None:
                region, page_vals = value_region(hit, words, spec, page_w, page_h, other_norms)
                roi_crop = crop(image, region)
                candidates = self.ocr.read_roi(roi_crop)
                if page_vals:
                    joined = " ".join(w.text for w in sorted(page_vals, key=lambda w: w.bbox.x1))
                    conf = float(np.mean([w.conf for w in page_vals]))
                    candidates.append(OCRCandidate(joined, conf, "page"))

            dec = self.engine.decide(spec, candidates, vlm_cand, roi_crop, region)
            if hit is None and not (vlm_cand and vlm_cand.text):
                dec.note = "anchor not found"
            if region is not None and roi_crop.size > 3:
                crop_path = crops_dir / f"{normalize(spec.name)}.png"
                cv2.imwrite(str(crop_path), roi_crop)
                dec.crop_path = str(crop_path.relative_to(crops_dir.parent.parent))
            decisions.append(dec)
        return decisions

    @staticmethod
    def _vlm_candidate(spec, vlm_values) -> OCRCandidate | None:
        v = vlm_values.get(spec.name) if vlm_values else None
        if not v:
            for k, val in (vlm_values or {}).items():
                if normalize(k) == normalize(spec.name):
                    v = val
                    break
        if v and str(v.get("value", "")).strip():
            return OCRCandidate(str(v["value"]).strip(), float(v.get("confidence", 0.7)), "vlm")
        return None

    def _finalize(self, doc_path, template, cls, decisions, image, run_dir, t0, note=""):
        fields = {d.name: d.to_public() for d in decisions}
        review = build_review_queue(decisions)
        accepted = sum(1 for d in decisions if d.status == "accepted")
        by_source = {}
        for d in decisions:
            by_source[d.source] = by_source.get(d.source, 0) + 1
        meta = {
            "pages_processed": 1,
            "engines": [e.name for e in self.ocr.engines],
            "vlm_provider": self.vlm.name,
            "fields_total": len(decisions),
            "fields_accepted": accepted,
            "fields_for_review": len(decisions) - accepted,
            "by_source": by_source,
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
        self._annotate(image, decisions, run_dir / "annotated.png")
        out_json = run_dir / "result.json"
        out_json.write_text(json.dumps(result.to_dict(), indent=2), encoding="utf-8")
        result.metadata["output"] = str(out_json)
        return result

    @staticmethod
    def _annotate(image, decisions, path):
        vis = image.copy()
        for d in decisions:
            if not d.roi:
                continue
            b = d.roi
            color = (0, 150, 0) if d.status == "accepted" else (0, 90, 230)
            cv2.rectangle(vis, (b.x1, b.y1), (b.x2, b.y2), color, 2)
            cv2.putText(vis, d.name[:16], (b.x1, max(14, b.y1 - 4)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 1, cv2.LINE_AA)
        cv2.imwrite(str(path), vis)
