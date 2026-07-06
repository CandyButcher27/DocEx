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


def _split_merged_options(merged_entry, opt_texts):
    """merged_entry's printed text visually concatenates several option labels into one OCR line
    (e.g. 'Graduate & Postgraduate' as a single detected box). Split its bbox into per-option
    sub-regions, ordered by where each option's first token appears in the merged string, so each
    option gets its own (approximate) checkbox region instead of the whole match being dropped."""
    lower = merged_entry["text"].lower()
    positions = []
    for ot in opt_texts:
        toks = _tokens(ot)
        idx = lower.find(toks[0]) if toks else -1
        positions.append((idx if idx != -1 else 0, ot))
    positions.sort(key=lambda p: p[0])
    x0, y0, x1, y1 = merged_entry["bbox"]
    width = x1 - x0
    total_chars = max(len(lower), 1)
    # boundary between two adjacent options sits at the next option's own character offset —
    # not an equal split — so "Graduate" (starts at char 0) gets less width than a naive 50/50
    # when "Postgraduate" (a longer word) starts partway through the line.
    starts = [idx for idx, _ in positions] + [total_chars]
    subs = {}
    for i, (_, ot) in enumerate(positions):
        sx0 = x0 + int(width * starts[i] / total_chars)
        sx1 = x0 + int(width * starts[i + 1] / total_chars)
        subs[ot] = (sx0, y0, sx1, y1)
    return subs


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
        # cells claimed by more than one option: either a genuine printed-label merge (2-3 options
        # sharing one OCR line, e.g. "Graduate & Postgraduate") — split proportionally and keep both
        # as separate candidates — or a real cross-match ambiguity (many options on one cell) — drop.
        keyf = lambda e: (e.get("page", 0),) + tuple(e["bbox"])
        by_key = {}
        for t, e in matches:
            by_key.setdefault(keyf(e), []).append((t, e))
        matches = []
        for group in by_key.values():
            if len(group) == 1:
                matches.append(group[0])
            elif len(group) <= 3:
                merged_entry = group[0][1]
                subs = _split_merged_options(merged_entry, [t for t, _ in group])
                for t, e in group:
                    synth = dict(e)
                    synth["bbox"] = subs[t]
                    matches.append((t, synth))
            # else: too many options collide on one cell — unrecoverable ambiguity, drop
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
            continue  # ambiguous — leave NO_OUTPUT for review
        out[f["path"]] = top_text
    return out


def _find_question_row(question_text, ocr_entries):
    """Find the OCR entry that best matches this question's text — unlike _find_option, this
    target may itself be a long paragraph-length OCR line, so no short-label cap here."""
    qt = _tokens(question_text)[:12]
    if not qt:
        return None
    qt = set(qt)
    best, best_score = None, 0.5
    for e in ocr_entries:
        et = set(_tokens(e["text"]))
        if not et:
            continue
        score = len(qt & et) / len(qt)
        if score > best_score:
            best, best_score = e, score
    return best


def _find_columns(ocr_entries, page, max_y):
    """Nearest standalone 'Yes'/'No' header pair on `page`, above `max_y` (the question's row)."""
    yes = [e for e in ocr_entries if e.get("page", 0) == page and re.fullmatch(r"yes", e["text"].strip().lower()) and e["bbox"][1] < max_y]
    no = [e for e in ocr_entries if e.get("page", 0) == page and re.fullmatch(r"no", e["text"].strip().lower()) and e["bbox"][1] < max_y]
    if not yes or not no:
        return None
    return max(yes, key=lambda e: e["bbox"][1]), max(no, key=lambda e: e["bbox"][1])


def detect_ticks(items, ocr_entries, pdf_path):
    """items: [{path, label}] — one per Yes/No question in a column-header matrix (the header's
    'Yes'/'No' printed once, then each question row has a blank tickbox under each column).
    Returns {path: 'Yes'|'No'}."""
    if not items:
        return {}
    pages = render_pages(pdf_path)
    out = {}
    for it in items:
        row = _find_question_row(it["label"], ocr_entries)
        if row is None:
            continue
        page = row.get("page", 0)
        if page >= len(pages):
            continue
        cols = _find_columns(ocr_entries, page, row["bbox"][1] + 4)
        if cols is None:
            continue
        ye, ne = cols
        img = pages[page]
        # x-columns come from the header's own "Yes"/"No" position; y-range is THIS question's
        # own row (not the header's) — each row's tickbox sits under the header, at its own height.
        row_y0, row_y1 = row["bbox"][1], row["bbox"][3]
        yes_bbox = (ye["bbox"][0], row_y0, ye["bbox"][2], row_y1)
        no_bbox = (ne["bbox"][0], row_y0, ne["bbox"][2], row_y1)
        yes_ink = _box_ink(img, yes_bbox)
        no_ink = _box_ink(img, no_bbox)
        if yes_ink < MIN_INK and no_ink < MIN_INK:
            continue
        top, other = (("Yes", yes_ink), ("No", no_ink)) if yes_ink >= no_ink else (("No", no_ink), ("Yes", yes_ink))
        if other[1] > 0 and top[1] < MARGIN * other[1]:
            continue  # ambiguous — leave NO_OUTPUT for review
        out[it["path"]] = top[0]
    return out
