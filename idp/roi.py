from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

import numpy as np

from .config import ANCHOR_MATCH_THRESHOLD
from .models import BBox, FieldSpec, OCRWord
from .textutil import normalize, similarity


COMMON_LABELS = {
    "Reference", "Cheque No", "Payee Bank", "Present/Permanent Address", "Email ID",
    "Landmark", "Landline No", "Mobile No", "in month/s", "Account Number", "IFSC Code",
    "Date of Birth", "Gender", "Nationality", "Occupation", "Annual Income", "ABHA Number",
    "Product Name", "Loan Type", "Relationship", "Date of First Loan disbursement",
}


@dataclass
class AnchorHit:
    bbox: BBox
    text: str
    score: float


_marker_re = re.compile(r"^\(?\d{1,2}[\).]$")


def _is_marker(text: str) -> bool:
    return bool(_marker_re.match(text.strip()))


def _same_line(a: BBox, b: BBox, tol: float = 0.6) -> bool:
    band = min(a.h, b.h) * tol
    return abs(a.cy - b.cy) <= max(band, 6)


def find_anchor(words: list[OCRWord], anchors: list[str]) -> Optional[AnchorHit]:
    best: Optional[AnchorHit] = None
    ordered = sorted(words, key=lambda w: (w.bbox.cy, w.bbox.x1))
    for anchor in anchors:
        n_anchor_tokens = max(1, len(anchor.split()))
        for i in range(len(ordered)):
            run: list[OCRWord] = []
            for j in range(i, min(i + n_anchor_tokens + 2, len(ordered))):
                w = ordered[j]
                if run and not _same_line(run[-1].bbox, w.bbox):
                    break
                run.append(w)
                joined = " ".join(x.text for x in run)
                sc = similarity(joined, anchor)
                if best is None or sc > best.score:
                    xs1 = min(x.bbox.x1 for x in run)
                    ys1 = min(x.bbox.y1 for x in run)
                    xs2 = max(x.bbox.x2 for x in run)
                    ys2 = max(x.bbox.y2 for x in run)
                    best = AnchorHit(BBox(xs1, ys1, xs2, ys2), joined, sc)
    if best and best.score >= ANCHOR_MATCH_THRESHOLD:
        return best
    return None


def _is_other_anchor(text: str, other_anchors: set[str]) -> bool:
    n = normalize(text)
    if len(n) < 4:
        return False
    for oa in other_anchors:
        on = normalize(oa)
        if len(on) < 4:
            continue
        if n in on or on in n:
            return True
        if similarity(text, oa) >= 0.6:
            return True
    return False


def value_region(
    anchor: AnchorHit,
    words: list[OCRWord],
    spec: FieldSpec,
    page_w: int,
    page_h: int,
    other_anchor_norms: set[str],
) -> tuple[BBox, list[OCRWord]]:
    a = anchor.bbox
    pad = max(4, int(a.h * 0.3))
    gap = max(6, int(a.h * 0.4))
    stops = other_anchor_norms | {normalize(c) for c in COMMON_LABELS}
    other_anchor_norms = stops

    def right_region() -> tuple[BBox, list[OCRWord]]:
        y1, y2 = a.y1 - pad, a.y2 + pad
        x_start = a.x2 + gap
        col_gap = int(page_w * 0.06)
        initial_gap = int(page_w * 0.30)
        line = sorted([w for w in words if w.bbox.x1 >= x_start - 2 and _same_line(a, w.bbox)],
                      key=lambda w: w.bbox.x1)
        found: list[OCRWord] = []
        prev_right = x_start
        first = True
        for w in line:
            thr = initial_gap if first else col_gap
            if w.bbox.x1 - prev_right > thr:
                break
            if _is_other_anchor(w.text, other_anchor_norms):
                break
            if _is_marker(w.text):
                prev_right = w.bbox.x2
                continue
            found.append(w)
            prev_right = w.bbox.x2
            first = False
        if found:
            x1 = min(w.bbox.x1 for w in found) - 4
            x2 = max(w.bbox.x2 for w in found) + 4
            yy1 = min(min(w.bbox.y1 for w in found), a.y1) - pad
            yy2 = max(max(w.bbox.y2 for w in found), a.y2) + pad
            region = BBox(max(0, x1), max(0, yy1), min(page_w, x2), min(page_h, yy2))
        else:
            region = BBox(x_start, max(0, y1),
                          min(page_w - 2, x_start + int(page_w * 0.18)), min(page_h, y2))
        return region, found

    def below_region() -> tuple[BBox, list[OCRWord]]:
        y_start = a.y2 + gap
        y_limit = min(page_h - 2, y_start + int(a.h * 3.0))
        x1, x2 = a.x1, min(page_w - 2, a.x1 + int(page_w * 0.30))
        region = BBox(max(0, x1), y_start, x2, y_limit)
        found = [w for w in words
                 if region.x1 <= w.bbox.cx <= region.x2 and y_start <= w.bbox.cy <= y_limit
                 and not _is_other_anchor(w.text, other_anchor_norms)]
        return region, found

    if spec.value_region == "below":
        return below_region()
    if spec.value_region == "right_then_below":
        reg, found = right_region()
        if found:
            return reg, found
        return below_region()
    return right_region()


def crop(image: np.ndarray, box: BBox) -> np.ndarray:
    x1 = max(0, box.x1)
    y1 = max(0, box.y1)
    x2 = min(image.shape[1], box.x2)
    y2 = min(image.shape[0], box.y2)
    if x2 <= x1 or y2 <= y1:
        return np.zeros((1, 1, 3), dtype=np.uint8)
    return image[y1:y2, x1:x2]
