import re

from ocr_engine import render_pages, ocr_image

MAX_WIDTH = 520
Y_PAD = 5
X_GAP = 6
MIN_LABEL_SCORE = 0.6
MAX_LABEL_TOKENS = 8      # anchor label lines must be short (skip paragraphs/questions)
ECHO_SCORE = 0.7          # drop recovered tokens that look like a known field label
MAX_VALUE_LEN = 45        # a field value isn't a sentence — reject longer recoveries
MAX_VALUE_TOKENS = 7

# Printed-label aliases per field path — real forms word labels differently from the schema.
ALIASES = {
    "loan_details.loan_account_number": ["Loan A/c No", "Loan Account No"],
    "loan_details.loanAppNumber": ["Loan Application No", "Proposal No", "CUST EMP ID Proposal Loan Application No"],
    "loan_details.loan_disbursement_date": ["Date of First Loan disbursement", "Date of Loan disbursement"],
    "loan_details.loanAmount": ["Loan Amount Sum Assured", "Sum Assured in Rs"],
    "insured_details.first_name": ["Name of the Insured Member", "Name of Insured Member", "Insured Member Name"],
    "insured_details.last_name": [],
    "insured_details.date_of_birth": ["Date of Birth of Insured Member", "Date of Birth of Insured"],
    "insured_details.height_cm": ["Height in cms", "Height"],
    "insured_details.weight_kg": ["Weight in kgs", "Weight"],
    "insured_details.annual_income": ["Annual Income"],
    "insured_details.pan_number": ["PAN Number", "PAN No"],
    "payment_details.premium_paid": ["Premium Amount", "Premium Paid"],
    "payment_details.payment_date": ["Payment Date"],
    "proposer_details.date_of_birth": ["Date of Birth"],
}


def _tokens(s):
    return [t for t in re.sub(r"[^a-z0-9]", " ", str(s).lower()).split() if t]


def _label_score(label_tokens, text):
    if not label_tokens:
        return 0.0, 0
    tt = set(_tokens(text))
    hits = len(label_tokens & tt)
    return hits / len(label_tokens), hits


def _find_anchor(variants, ocr_entries):
    best, best_score = None, MIN_LABEL_SCORE
    for e in ocr_entries:
        if len(_tokens(e["text"])) > MAX_LABEL_TOKENS:
            continue
        for lab in variants:
            lt = set(_tokens(lab))
            need = min(2, len(lt))
            score, hits = _label_score(lt, e["text"])
            if hits >= need and score > best_score:
                best, best_score = e, score
    return best


def _is_label(text, all_labels):
    if len(_tokens(text)) > MAX_LABEL_TOKENS:
        return False
    for lab in all_labels:
        lt = set(_tokens(lab))
        if lt and _label_score(lt, text)[0] >= ECHO_SCORE:
            return True
    return False


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


def _clean_value(tokens, variants, all_labels):
    lset = set()
    for v in variants:
        lset |= set(_tokens(v))
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
    pages = None
    recovered = {}
    for f in missing:
        variants = [f["label"]] + ALIASES.get(f["path"], [])
        anchor = _find_anchor(variants, ocr_entries)
        if anchor is None:
            continue
        page_idx = anchor.get("page", 0)
        x0, y0, x1, y1 = anchor["bbox"]

        # (1) value already detected as OCR token(s) right of the label on the same row?
        row_right = [
            e for e in ocr_entries
            if e is not anchor and e.get("page", 0) == page_idx
            and e["bbox"][1] < y1 and e["bbox"][3] > y0 and e["bbox"][0] > x1
        ]
        row_right.sort(key=lambda e: e["bbox"][0])
        val_tokens = []
        for e in row_right:
            if e["bbox"][0] > x1 + MAX_WIDTH or _is_label(e["text"], all_labels):
                break
            val_tokens.append(e)
        value = _clean_value(val_tokens, variants, all_labels) if val_tokens else ""

        # (2) nothing detected there → re-OCR the region (value handwritten, missed by full-page detection)
        if not value:
            if pages is None:
                pages = render_pages(pdf_path)
            if page_idx >= len(pages):
                continue
            img = pages[page_idx]
            w, h = img.size
            cx0, cy0 = x1 + X_GAP, max(0, y0 - Y_PAD)
            cx1, cy1 = _right_bound(anchor, ocr_entries, w), min(h, y1 + Y_PAD)
            if cx1 - cx0 >= 20 and cy1 - cy0 >= 8:
                value = _clean_value(ocr_image(img.crop((cx0, cy0, cx1, cy1))), variants, all_labels)

        if value and len(value) <= MAX_VALUE_LEN and len(value.split()) <= MAX_VALUE_TOKENS:
            recovered[f["path"]] = value
    return recovered
