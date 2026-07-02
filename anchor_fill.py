import re

from ocr_engine import render_pages, ocr_image

MAX_WIDTH = 520
Y_PAD = 5
X_GAP = 6
MIN_LABEL_SCORE = 0.6
MAX_LABEL_TOKENS = 8      # anchor label lines must be short (skip paragraphs/questions)
ECHO_SCORE = 0.7          # drop recovered tokens that look like a known field label


def _tokens(s):
    return [t for t in re.sub(r"[^a-z0-9]", " ", str(s).lower()).split() if t]


def _label_score(label_tokens, text):
    if not label_tokens:
        return 0.0, 0
    tt = set(_tokens(text))
    hits = len(label_tokens & tt)
    return hits / len(label_tokens), hits


def _find_anchor(label, ocr_entries):
    lt = set(_tokens(label))
    need = min(2, len(lt))
    best, best_score = None, MIN_LABEL_SCORE
    for e in ocr_entries:
        if len(_tokens(e["text"])) > MAX_LABEL_TOKENS:
            continue
        score, hits = _label_score(lt, e["text"])
        if hits >= need and score > best_score:
            best, best_score = e, score
    return best


def _right_bound(anchor, ocr_entries, w):
    x0, y0, x1, y1 = anchor["bbox"]
    page = anchor.get("page", 0)
    limit = x1 + MAX_WIDTH
    for e in ocr_entries:
        if e is anchor or e.get("page", 0) != page:
            continue
        ex0, ey0, ex1, ey1 = e["bbox"]
        if ey0 < y1 and ey1 > y0 and ex0 > x1 + X_GAP:   # same row band, to the right
            limit = min(limit, ex0 - X_GAP)
    return min(w, limit)


def _clean_value(tokens, label, all_labels):
    lset = set(_tokens(label))
    parts = []
    for t in tokens:
        toks = set(_tokens(t["text"]))
        if not toks:
            continue
        if toks <= lset:                 # echo of this field's own label
            continue
        drop = False
        for lab in all_labels:           # echo of a neighboring field's label
            lt = set(_tokens(lab))
            if lt and len(lt & toks) / len(lt) >= ECHO_SCORE:
                drop = True
                break
        if drop:
            continue
        parts.append(t["text"].strip())
    return " ".join(p for p in parts if p).strip()


def anchor_fill(missing, ocr_entries, pdf_path, all_labels=None):
    """missing: [{path, label}]. Re-OCR the region right of each field's printed label; return {path: value}."""
    if not missing:
        return {}
    all_labels = all_labels or []
    pages = render_pages(pdf_path)
    recovered = {}
    for f in missing:
        anchor = _find_anchor(f["label"], ocr_entries)
        if anchor is None:
            continue
        page_idx = anchor.get("page", 0)
        if page_idx >= len(pages):
            continue
        img = pages[page_idx]
        w, h = img.size
        x0, y0, x1, y1 = anchor["bbox"]
        cx0 = x1 + X_GAP
        cy0 = max(0, y0 - Y_PAD)
        cx1 = _right_bound(anchor, ocr_entries, w)
        cy1 = min(h, y1 + Y_PAD)
        if cx1 - cx0 < 20 or cy1 - cy0 < 8:
            continue
        tokens = ocr_image(img.crop((cx0, cy0, cx1, cy1)))
        value = _clean_value(tokens, f["label"], all_labels)
        if value:
            recovered[f["path"]] = value
    return recovered
