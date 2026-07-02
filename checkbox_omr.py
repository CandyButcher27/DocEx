import re
import statistics
from collections import Counter

from ocr_engine import render_pages

INK_THRESH = 140     # pixel < this = ink (0=black, 255=white)
MIN_INK = 0.06       # min dark-pixel ratio in a box to count as marked
MARGIN = 1.6         # winner must beat runner-up ink by this factor
LABEL_MATCH = 0.6    # min token-overlap to accept an option label match
MIN_GROUP_FRAC = 0.4  # min fraction of a field's options that must be present as printed labels
MIN_GROUP_OPTS = 2    # ...and at least this many, else it's not a real checkbox group


def _tokens(s):
    return [t for t in re.sub(r"[^a-z0-9]", " ", str(s).lower()).split() if t]


def _norm2(s):
    return re.sub(r"[^a-z0-9<>=%/.-]", "", str(s).lower())


def _match_score(option_text, text):
    # symbol-bearing options (>=50%, <50%) must match symbols exactly, not just digits
    if any(c in option_text for c in "<>=%"):
        o2, t2 = _norm2(option_text), _norm2(text)
        return 1.0 if o2 and o2 in t2 else 0.0
    ot = set(_tokens(option_text))
    if not ot:
        return 0.0
    tt = set(_tokens(text))
    return len(ot & tt) / len(ot)


def _find_option(option_text, ocr_entries):
    best, best_score = None, LABEL_MATCH
    for e in ocr_entries:
        s = _match_score(option_text, e["text"])
        if s > best_score:
            best, best_score = e, s
    return best


def _ink_ratio(gray_crop):
    px = list(gray_crop.getdata())
    if not px:
        return 0.0
    dark = sum(1 for p in px if p < INK_THRESH)
    return dark / len(px)


def _box_ink(page_img, label_bbox):
    """Max ink ratio in the checkbox regions immediately left/right of the option label."""
    x0, y0, x1, y1 = label_bbox
    h = y1 - y0
    if h <= 0:
        return 0.0
    boxw = int(h * 1.4)
    W, H = page_img.size
    gray = page_img.convert("L")
    regions = [
        (max(0, x0 - boxw - 4), y0, max(0, x0 - 4), y1),   # left of label
        (min(W, x1 + 4), y0, min(W, x1 + 4 + boxw), y1),   # right of label
    ]
    best = 0.0
    for rx0, ry0, rx1, ry1 in regions:
        if rx1 - rx0 < 4 or ry1 - ry0 < 4:
            continue
        best = max(best, _ink_ratio(gray.crop((rx0, ry0, rx1, ry1))))
    return best


def detect(coded_fields, ocr_entries, pdf_path):
    """coded_fields: [{path, label, options:[{text,value}]}]. Returns {path: winning_option_text}."""
    if not coded_fields:
        return {}
    pages = render_pages(pdf_path)
    out = {}
    for f in coded_fields:
        matches = []
        for o in f["options"]:
            e = _find_option(o["text"], ocr_entries)
            if e is not None and e.get("page", 0) < len(pages):
                matches.append((o["text"], e))
        # drop cells claimed by more than one option (can't disambiguate)
        keyf = lambda e: (e.get("page", 0),) + tuple(e["bbox"])
        cnt = Counter(keyf(e) for _, e in matches)
        matches = [(t, e) for t, e in matches if cnt[keyf(e)] == 1]
        if len(matches) < MIN_GROUP_OPTS:
            continue
        # spatial cluster: option labels of one group sit together — drop cross-region outliers
        ycs = [(e["bbox"][1] + e["bbox"][3]) / 2 for _, e in matches]
        med = statistics.median(ycs)
        tol = max(150, 4 * statistics.median([e["bbox"][3] - e["bbox"][1] for _, e in matches]))
        pg = statistics.median([e.get("page", 0) for _, e in matches])
        matches = [(t, e) for (t, e), yc in zip(matches, ycs) if abs(yc - med) <= tol and e.get("page", 0) == pg]
        if len(matches) < MIN_GROUP_OPTS or len(matches) / len(f["options"]) < MIN_GROUP_FRAC:
            continue  # not a real printed checkbox group
        scored = sorted(((_box_ink(pages[e.get("page", 0)], e["bbox"]), t) for t, e in matches), reverse=True)
        top_ink, top_text = scored[0]
        runner = scored[1][0] if len(scored) > 1 else 0
        if top_ink < MIN_INK:
            continue
        if runner > 0 and top_ink < MARGIN * runner:
            continue  # ambiguous — leave for review
        out[f["path"]] = top_text
    return out
