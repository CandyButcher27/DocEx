import re
from statistics import median

from checkbox_omr import _match_score
from anchor_fill import MAX_VALUE_LEN, MAX_VALUE_TOKENS

# nominee_details is printed as a table: one header row (column labels) then one x-aligned data
# row per nominee below it — anchor_fill's row-based "value right of label" heuristic can't match
# this layout, so column position is derived from the header instead.
COL_ALIASES = {
    "first_name": ["Nominee Name"],
    "middle_name": ["Nominee Name"],
    "last_name": ["Nominee Name"],
    "date_of_birth": ["Date of Birth"],
    "percentage_share": ["Percentage Share", "Share"],
    "mobile_no": ["Mobile No"],
    "email_id": ["E-mail ID", "Email ID"],
    "address_line_1": ["Present/Permanent Address", "Address"],
    "account_number": ["Account Number"],
    "ifsc_code": ["IFSC Code"],
}
SECTION_ANCHOR = ["Nominee", "Appointee", "Details"]
HEADER_MIN_COLS = 4       # min distinct columns matched before trusting a header block exists
HEADER_MATCH_SCORE = 0.6  # min token-overlap to accept a header-cell match
COL_SLACK = 20            # x-px slack around a derived column band (proportional char-offset splitting isn't pixel-exact on non-monospace text)
NEAREST_MARGIN = 1.6      # a token must be this much closer to its best band than the runner-up, else drop (ambiguous, matches checkbox_omr.MARGIN)


def _tokens(s):
    return [t for t in re.sub(r"[^a-z0-9]", " ", str(s).lower()).split() if t]


def _yc(e):
    return (e["bbox"][1] + e["bbox"][3]) / 2


def _height(e):
    return e["bbox"][3] - e["bbox"][1]


def _find_section_anchor(ocr_entries):
    best, best_score = None, HEADER_MATCH_SCORE
    for e in ocr_entries:
        s = _match_score(" ".join(SECTION_ANCHOR), e["text"])
        if s > best_score:
            best, best_score = e, s
    return best


def _find_header_block(ocr_entries, page, y_floor):
    """Individual OCR tokens, not joined lines — each printed cell (even a wrapped one like
    'Relationship' / 'with Life' / 'Details' / 'Insured') is its own entry. The header's physical
    location isn't known ahead of time (other rows — product name, appointee fields — sit between
    the section title and the real header), so: match every candidate token against COL_ALIASES
    first, then cluster ONLY the matched tokens by y-proximity and take the densest cluster as the
    header block, rather than assuming a fixed offset below y_floor."""
    candidates = [e for e in ocr_entries if e.get("page", 0) == page and e["bbox"][1] >= y_floor]
    if not candidates:
        return None
    heights = [_height(e) for e in candidates if _height(e) > 0]
    row_h = median(heights) if heights else 12

    hits = []  # (entry, key)
    for e in candidates:
        best_key, best_score = None, HEADER_MATCH_SCORE
        for key, phrases in COL_ALIASES.items():
            for ph in phrases:
                s = _match_score(ph, e["text"])
                if s > best_score:
                    best_key, best_score = key, s
        if best_key:
            hits.append((e, best_key))
    if not hits:
        return None

    hits.sort(key=lambda h: _yc(h[0]))
    tol = row_h * 2.5
    clusters, cur, cur_y = [], [], None
    for e, key in hits:
        yc = _yc(e)
        if cur_y is None or yc - cur_y <= tol:
            cur.append((e, key))
            cur_y = yc
        else:
            clusters.append(cur)
            cur = [(e, key)]
            cur_y = yc
    if cur:
        clusters.append(cur)

    def distinct_count(cluster):
        keys = {k for _, k in cluster}
        cols = {k for k in keys if k not in ("first_name", "middle_name", "last_name")}
        if "first_name" in keys:
            cols.add("name")
        return len(cols)

    best_cluster = max(clusters, key=distinct_count)
    if distinct_count(best_cluster) < HEADER_MIN_COLS:
        return None

    matched = {}
    for e, key in best_cluster:
        matched.setdefault(key, []).append(e)
    y0 = min(_yc(e) for e, _ in best_cluster)
    y1 = max(_yc(e) for e, _ in best_cluster)
    return {"page": page, "y0": y0, "y1": y1, "row_h": row_h, "matched": matched}


def _column_bands(header):
    bands = {}
    for key, entries in header["matched"].items():
        x0 = min(e["bbox"][0] for e in entries)
        x1 = max(e["bbox"][2] for e in entries)
        bands[key] = (x0 - COL_SLACK, x1 + COL_SLACK)
    return bands


def _find_data_rows(ocr_entries, header, max_index):
    """Locate each 'Nominee N' row-label marker below the header block. On the observed form the
    marker text sits at the BOTTOM of its row's wrapped content block (other cells in the same row
    print above it, not below), so a row's band runs from the previous row boundary (or the header)
    UP TO this marker — not downward from it."""
    page = header["page"]
    below = [e for e in ocr_entries if e.get("page", 0) == page and e["bbox"][1] > header["y1"]]
    markers = {}
    for e in below:
        toks = _tokens(e["text"])
        if len(toks) >= 2 and toks[0] == "nominee" and toks[1].isdigit():
            idx = int(toks[1]) - 1
            if idx not in markers or e["bbox"][1] < markers[idx]["bbox"][1]:
                markers[idx] = e
    rows = {}
    sorted_idxs = sorted(markers)
    prev_bottom = header["y1"] + header["row_h"] * 0.5   # gap so a header token's own yc doesn't slip into row 0
    for idx in sorted_idxs:
        if idx > max_index:
            continue
        marker_y = markers[idx]["bbox"][1]
        y1 = marker_y + header["row_h"] * 1.5   # marker's own row can wrap a continuation line below it
        rows[idx] = (prev_bottom, y1)
        prev_bottom = y1
    return rows


def _split_row_entry(e):
    """A data-row cell can get OCR-merged across several columns into one box (e.g.
    '1001. 8610987289 SAMEASABOUE.' spanning percentage_share/mobile_no/address_line_1) — split
    it into per-whitespace-token virtual entries, each with an x-sub-bbox proportional to its
    character offset within the original text, so each token can independently match its own
    column band instead of the whole blob claiming just one."""
    text = e["text"]
    parts = text.split(" ")
    if len(parts) <= 1:
        return [e]
    x0, y0, x1, y1 = e["bbox"]
    width = x1 - x0
    total = len(text)
    out, pos = [], 0
    for part in parts:
        start = text.find(part, pos)
        end = start + len(part)
        pos = end
        sx0 = x0 + int(width * start / total)
        sx1 = x0 + int(width * end / total)
        out.append({"text": part, "bbox": (sx0, y0, sx1, y1), "page": e.get("page", 0)})
    return out


def _split_name(value):
    toks = value.split()
    if len(toks) <= 1:
        return {"first_name": value, "middle_name": "", "last_name": ""}
    if len(toks) == 2:
        return {"first_name": toks[0], "middle_name": "", "last_name": toks[1]}
    return {"first_name": toks[0], "middle_name": " ".join(toks[1:-1]), "last_name": toks[-1]}


def extract_nominee_table(missing, ocr_entries, pdf_path):
    """missing: [{path: 'nominee_details[i].leaf', label}]. Returns {path: value}."""
    if not missing:
        return {}

    by_index = {}
    for f in missing:
        m = re.match(r"nominee_details\[(\d+)\]\.(.+)", f["path"])
        if not m:
            continue
        idx, leaf = int(m.group(1)), m.group(2)
        by_index.setdefault(idx, set()).add(leaf)
    if not by_index:
        return {}
    max_index = max(by_index)

    section_anchor = _find_section_anchor(ocr_entries)
    y_floor = section_anchor["bbox"][1] if section_anchor else 0
    pages = sorted({e.get("page", 0) for e in ocr_entries})

    out = {}
    resolved_indices = set()
    for page in pages:
        floor = y_floor if section_anchor and section_anchor.get("page", 0) == page else 0
        while True:
            header = _find_header_block(ocr_entries, page, floor)
            if header is None:
                break
            bands = _column_bands(header)
            data_rows = _find_data_rows(ocr_entries, header, max_index)
            for idx, leaves in by_index.items():
                if idx in resolved_indices or idx not in data_rows:
                    continue
                row_y0, row_y1 = data_rows[idx]
                row_entries = []
                for e in ocr_entries:
                    if e.get("page", 0) == page and row_y0 <= _yc(e) <= row_y1:
                        row_entries.extend(_split_row_entry(e))
                needed_keys = {("first_name" if leaf in ("first_name", "middle_name", "last_name") else leaf) for leaf in leaves}
                # each token is assigned to its single NEAREST band, not every band whose slack it
                # falls within — otherwise a value near a column boundary (e.g. mobile_no/email_id
                # adjacent bands both covering it) gets duplicated into both columns
                by_key = {}
                for e in row_entries:
                    ec = (e["bbox"][0] + e["bbox"][2]) / 2
                    dists = []
                    for key in needed_keys:
                        band = bands.get(key)
                        if band is None:
                            continue
                        bx0, bx1 = band
                        if bx0 <= ec <= bx1:
                            dists.append((abs(ec - (bx0 + bx1) / 2), key))
                    if not dists:
                        continue
                    dists.sort()
                    best_dist, best_key = dists[0]
                    if len(dists) > 1 and best_dist * NEAREST_MARGIN >= dists[1][0]:
                        continue  # near-tie between two columns — don't guess
                    by_key.setdefault(best_key, []).append(e)

                cell_values = {}
                for key, cell in by_key.items():
                    cell.sort(key=lambda e: (e["bbox"][1], e["bbox"][0]))
                    value = " ".join(e["text"].strip() for e in cell if e["text"].strip())
                    if value and len(value) <= MAX_VALUE_LEN and len(value.split()) <= MAX_VALUE_TOKENS:
                        cell_values[key] = value

                for leaf in leaves:
                    path = f"nominee_details[{idx}].{leaf}"
                    if leaf in ("first_name", "middle_name", "last_name"):
                        name_val = cell_values.get("first_name")
                        if name_val:
                            split_val = _split_name(name_val)[leaf]
                            if split_val:
                                out[path] = split_val
                    elif leaf in cell_values:
                        out[path] = cell_values[leaf]
                resolved_indices.add(idx)
            floor = header["y1"] + header["row_h"]
    return out
