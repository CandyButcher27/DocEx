import copy
import json
import re
from pathlib import Path
from statistics import median

from llm_client import run_extraction
from validators import validate

ROOT = Path(__file__).parent
SPEC_FILE = ROOT / "data" / "field_spec.json"
CODE_MAPPER_FILE = ROOT / "data" / "code_mapper.json"
TEMPLATE_FILE = ROOT / "data" / "template.json"

_spec = None
_mapper = None
_blanked_template = None


def load_spec():
    global _spec
    if _spec is None:
        _spec = json.loads(SPEC_FILE.read_text(encoding="utf-8"))
    return _spec


def load_mapper():
    global _mapper
    if _mapper is None:
        _mapper = json.loads(CODE_MAPPER_FILE.read_text(encoding="utf-8"))
    return _mapper


def _blank(node):
    if isinstance(node, dict):
        return {k: _blank(v) for k, v in node.items()}
    if isinstance(node, list):
        if node and isinstance(node[0], dict):
            return [_blank(node[0])]
        return []
    return ""


def blank_skeleton():
    """Deep copy of data/template.json (master schema shape) with every scalar leaf blanked to ''."""
    global _blanked_template
    if _blanked_template is None:
        template = json.loads(TEMPLATE_FILE.read_text(encoding="utf-8"))
        _blanked_template = _blank(template)
    return copy.deepcopy(_blanked_template)


def _fixed_specs(include_medical=True):
    m = load_mapper()
    dec = [{"code": o["code"], "text": o["text"]} for o in m["declaration"]]
    specs = {}
    if include_medical:
        med = [{"code": o["id"], "text": o["text"]} for o in m["medicalQuestionOptions"] if o["id"].startswith("1000")]
        specs["medical_lifestyle_questions"] = {"section": "Medical Questions", "answer_key": "medical_answers", "items": med, "description": True}
    specs["declaration"] = {"section": "Declaration", "answer_key": "declaration_answers", "items": dec, "description": False}
    return specs


def include_medical_for(doc_type):
    """DOGH templates print no medical questions at all (0/9 matched in every DOGH docx studied,
    vs 7/9 in every LFQ docx) — a genuine content difference, not an inferred one. DOGH/LFQ
    cosine separation (~0.87-0.89) is well clear of same-type product-pair near-duplicates
    (Premier/Secure, 0.94-0.996), so trust an explicit "DOGH" match; anything else (unmatched,
    LFQ, or no doc_type at all) keeps the safe full-schema default."""
    return not (doc_type and "DOGH" in doc_type)


def _norm(s):
    return re.sub(r"[^a-z0-9]", "", str(s).lower())


def _trunc(s, n=70):
    s = str(s).replace("\n", " ")
    return s if len(s) <= n else s[: n - 1] + "…"


VARIABLE_GROUPS = ("nominee_details", "address_details")
FIXED_GROUPS = ("medical_lifestyle_questions", "declaration")
SKIP_GROUPS = ("documents", "otp_details")
SUSPECT_SECTIONS = ("proposer_details", "mph_section")
NAME_GATED_SECTIONS = ("proposer_details",)
MAX_INSTANCES = 10
YESNO_OPTIONS = [{"text": "Yes", "value": "Yes"}, {"text": "No", "value": "No"}]
# Paths that are the SAME physical form field as another path (per mapping_report.docx).
# Ask the LLM once for the source and mirror it, instead of asking twice — two independent
# asks for one printed field let the model drift (echoing a neighboring blank field's label
# into one of the two instead of NOT_FOUND).
MIRROR_FIELDS = {"premium": "payment_details.premium_paid"}


def _leaf(path):
    return path.split("].", 1)[1] if "]." in path else path


def _norm_index(path):
    return re.sub(r"\[\d+\]", "[0]", path)


def _group_templates(spec):
    groups = {}
    for f in spec["fields"]:
        if f["repeat_group"] in VARIABLE_GROUPS:
            groups.setdefault(f["repeat_group"], []).append((_leaf(f["path"]), f))
    return groups


def _allowed(f):
    if "allowed_values" not in f:
        return ""
    vals = [_trunc(v, 50) for v in f["allowed_values"][:40]]
    return "  (allowed: " + " | ".join(vals) + ")"


def build_prompt(spec):
    groups = _group_templates(spec)
    lines = [
        "You are a document field extractor. You are given OCR text from a scanned form as JSON: pages with lines in natural reading order (top-to-bottom, left-to-right).",
        "A field's value usually sits to the RIGHT of its printed label on the same line, or on the line just below it. Printed labels on the form may be worded differently from the field names below (e.g. 'Loan A/c No.' = Loan Account Number, 'Name of the Insured Member' = First/Middle/Last Name) — match them by meaning.",
        "Return ONLY one JSON object.",
        "For non-repeating fields, use the exact PATH string below as the key.",
        'If a field is not present, use "NOT_FOUND".',
        "For fields that list allowed values, return EXACTLY one of the listed human-readable values (never a code).",
        "For repeating sections, use the group key with an ARRAY of objects — one object per entry found in the document, [] if none. Each object's keys are the leaf names shown.",
        "Use the section headers only as context to disambiguate similar labels.",
        "",
        "Non-repeating fields:",
    ]
    skip = VARIABLE_GROUPS + FIXED_GROUPS + SKIP_GROUPS
    by_section = {}
    for f in spec["fields"]:
        if f["repeat_group"] in skip:
            continue
        by_section.setdefault(f["section"] or "Other", []).append(f)
    for section, fields in by_section.items():
        lines.append(f"[{section}]")
        for f in fields:
            lines.append(f'- {f["path"]} : {f["label"]}{_allowed(f)}')
        lines.append("")
    for g, leaves in groups.items():
        lines.append(f'Repeating section — JSON key "{g}" = array of objects (one per entry, [] if none). Object keys:')
        for leaf, f in leaves:
            lines.append(f'  - {leaf} : {f["label"]}{_allowed(f)}')
        lines.append("")
    for g, fx in _fixed_specs(include_medical=True).items():
        lines.append(f'{fx["section"]} — JSON key "{fx["answer_key"]}" = object mapping each code below to "Yes", "No", or "NOT_FOUND" (the applicant\'s answer/tick in the document):')
        for item in fx["items"]:
            lines.append(f'  - {item["code"]} : {_trunc(item["text"], 90)}')
        lines.append("")
    return "\n".join(lines)


def _parse_obj(raw):
    m = re.search(r"\{.*\}", raw, re.DOTALL)
    if not m:
        return {}
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return {}


def _chunks(seq, n):
    for i in range(0, len(seq), n):
        yield seq[i:i + n]


_BATCH_HEADER = (
    "You are a document field extractor. The OCR text is given as pages of lines in natural reading order. "
    "A field's value usually sits to the RIGHT of its printed label on the same line, or on the line just below. "
    "Printed labels may be worded differently from the field names (e.g. 'Loan A/c No.' = Loan Account Number, "
    "'Name of the Insured Member' = First/Middle/Last Name) — match by meaning. "
    "Only fill a field when the value is clearly written for THAT specific label/section on the form. "
    "If a section or field is blank, empty, or not present, return \"NOT_FOUND\" — never copy a value from a different field or section to fill it. "
    "When a person's name has only two tokens, put them in first_name and last_name (leave middle_name NOT_FOUND). "
    "Return ONLY one JSON object and include EVERY key listed, using \"NOT_FOUND\" when the value is absent."
)


def _run_batches(spec, pages, batch_size=15, fixed_specs=None):
    fixed_specs = _fixed_specs() if fixed_specs is None else fixed_specs
    user = {"pages": pages}
    parsed = {}
    singles = [
        f for f in spec["fields"]
        if f["repeat_group"] not in VARIABLE_GROUPS + FIXED_GROUPS + SKIP_GROUPS
        and f["path"] not in MIRROR_FIELDS
    ]
    for chunk in _chunks(singles, batch_size):
        lines = [_BATCH_HEADER, "", "For coded fields choose exactly one listed allowed value (the human text, not a code).", "", "Fields (JSON keys):"]
        for f in chunk:
            lines.append(f'- {f["path"]} : {f["label"]}{_allowed(f)}')
        parsed.update(_parse_obj(run_extraction(user, "\n".join(lines))))
    for g, leaves in _group_templates(spec).items():
        lines = [
            _BATCH_HEADER, "",
            f'Extract the repeating section. Return ONLY {{"{g}": [ ... ]}} — a JSON array with one object per entry present in the document ([] if none).',
            "Each object's keys (choose one allowed value for coded keys):",
        ]
        for leaf, f in leaves:
            lines.append(f'- {leaf} : {f["label"]}{_allowed(f)}')
        obj = _parse_obj(run_extraction(user, "\n".join(lines)))
        parsed[g] = obj.get(g, [])
    for g, fx in fixed_specs.items():
        lines = [
            _BATCH_HEADER, "",
            f'For each question code below, return the applicant\'s ticked answer. Return ONLY {{"{fx["answer_key"]}": {{code: "Yes"|"No"|"NOT_FOUND"}}}}.',
            "Codes:",
        ]
        for item in fx["items"]:
            lines.append(f'  - {item["code"]} : {_trunc(item["text"], 90)}')
        obj = _parse_obj(run_extraction(user, "\n".join(lines)))
        parsed[fx["answer_key"]] = obj.get(fx["answer_key"], {})
    return parsed


def _decode(spec, flat):
    opt = {}
    for f in spec["fields"]:
        if "options" in f:
            opt[_norm_index(f["path"])] = {_norm(o["text"]): o["value"] for o in f["options"]}
    out = {}
    for path, val in flat.items():
        k = _norm_index(path)
        if val == "NOT_FOUND" or k not in opt:
            out[path] = val
        else:
            out[path] = opt[k].get(_norm(val), val)
    return out


def assemble(flat):
    root = blank_skeleton()
    group_templates = {k: copy.deepcopy(v[0]) for k, v in root.items() if isinstance(v, list) and v and isinstance(v[0], dict)}
    for path, val in flat.items():
        if val == "NOT_FOUND":
            continue
        _set_path(root, path, val, group_templates)
    _finalize_fixed(root)
    return root


def _finalize_fixed(root):
    for g in FIXED_GROUPS:
        arr = root.get(g)
        if isinstance(arr, list):
            for e in arr:
                e["answer"] = e.get("answer", "")
                e["isAnswer"] = e["answer"] == "Yes"
                if g == "medical_lifestyle_questions":
                    e["description"] = e.get("description", "")
    return root


def _set_path(root, path, val, group_templates=None):
    group_templates = group_templates or {}
    tokens = path.split(".")
    cur = root
    for i, tok in enumerate(tokens):
        m = re.match(r"^([^\[]+)(?:\[(\d+)\])?$", tok)
        key, idx = m.group(1), m.group(2)
        last = i == len(tokens) - 1
        if idx is None:
            if last:
                cur[key] = val
            else:
                cur = cur.setdefault(key, {})
        else:
            idx = int(idx)
            arr = cur.setdefault(key, [])
            blank_item = group_templates.get(key)
            while len(arr) <= idx:
                arr.append(copy.deepcopy(blank_item) if blank_item is not None else {})
            if last:
                arr[idx] = val
            else:
                cur = arr[idx]
    return root


def reading_order(ocr_entries):
    """Cluster OCR tokens into visual rows (sort by y then x) so label:value pairs sit on one line."""
    by_page = {}
    for e in ocr_entries:
        by_page.setdefault(e.get("page", 0), []).append(e)
    pages = []
    for p in sorted(by_page):
        toks = by_page[p]
        heights = [e["bbox"][3] - e["bbox"][1] for e in toks if e["bbox"][3] > e["bbox"][1]]
        tol = (median(heights) * 0.6) if heights else 10
        toks.sort(key=lambda e: (e["bbox"][1] + e["bbox"][3]) / 2)
        rows, cur, cur_y = [], [], None
        for e in toks:
            yc = (e["bbox"][1] + e["bbox"][3]) / 2
            if cur_y is None or abs(yc - cur_y) <= tol:
                cur.append(e)
                cur_y = sum((t["bbox"][1] + t["bbox"][3]) / 2 for t in cur) / len(cur)
            else:
                rows.append(cur)
                cur, cur_y = [e], yc
        if cur:
            rows.append(cur)
        lines = []
        for r in rows:
            r.sort(key=lambda e: e["bbox"][0])
            line = "   ".join(t["text"] for t in r if t["text"].strip())
            if line:
                lines.append(line)
        pages.append({"page": p, "lines": lines})
    return pages


def _confidence(value_human, ocr_entries):
    nv = _norm(value_human)
    if not nv:
        return None
    best = None
    for e in ocr_entries:
        nt = _norm(e.get("text", ""))
        if nv in nt:
            c = e.get("confidence")
            if c is not None and (best is None or c > best):
                best = c
    return best


def extract(ocr_entries, spec=None, threshold=0.95, pdf_path=None, doc_type=None):
    spec = spec or load_spec()
    groups = _group_templates(spec)
    fixed_specs = _fixed_specs(include_medical=include_medical_for(doc_type))
    parsed = _run_batches(spec, reading_order(ocr_entries), fixed_specs=fixed_specs)

    skip = VARIABLE_GROUPS + FIXED_GROUPS + SKIP_GROUPS
    metas = []
    flat_human = {}
    for f in spec["fields"]:
        if f["repeat_group"] in skip:
            continue
        p = f["path"]
        flat_human[p] = str(parsed.get(p, "NOT_FOUND"))
        metas.append((p, f))
    for g, leaves in groups.items():
        instances = parsed.get(g)
        if not isinstance(instances, list):
            instances = []
        for i, inst in enumerate(instances[:MAX_INSTANCES]):
            if not isinstance(inst, dict):
                continue
            for leaf, f in leaves:
                p = f"{g}[{i}].{leaf}"
                flat_human[p] = str(inst.get(leaf, "NOT_FOUND"))
                metas.append((p, f))
    for g, fx in fixed_specs.items():
        ans_map = parsed.get(fx["answer_key"])
        if not isinstance(ans_map, dict):
            ans_map = {}
        for i, item in enumerate(fx["items"]):
            code = item["code"]
            cpath = f"{g}[{i}].code"
            flat_human[cpath] = code
            metas.append((cpath, {"path": cpath, "label": "Code", "section": fx["section"], "coded": False, "readonly": True}))
            apath = f"{g}[{i}].answer"
            raw_ans = str(ans_map.get(code, "NOT_FOUND")).strip().lower()
            ans = "Yes" if raw_ans in ("yes", "y", "true") else "No" if raw_ans in ("no", "n", "false") else "NOT_FOUND"
            flat_human[apath] = ans
            metas.append((apath, {"path": apath, "label": _trunc(item["text"], 90), "section": fx["section"], "coded": False, "answer_field": True, "options": YESNO_OPTIONS}))

    anchor_paths = set()
    notes = {}
    state_override = {}
    if pdf_path:
        missing = [
            {"path": p, "label": f["label"]}
            for p, f in metas
            if not f.get("repeat_group") and not f["coded"] and not f.get("readonly")
            and not f.get("answer_field") and "options" not in f
            and not p.startswith(SUSPECT_SECTIONS)
            and p not in MIRROR_FIELDS
            and flat_human[p] == "NOT_FOUND"
        ]
        from anchor_fill import anchor_fill
        all_labels = [f["label"] for f in spec["fields"]]
        recovered = anchor_fill(missing, ocr_entries, pdf_path, all_labels)
        for p, val in recovered.items():
            flat_human[p] = val
            anchor_paths.add(p)

        # nominee_details prints as a header row + one x-aligned data row per nominee (a table,
        # not label:value lines), so it needs its own column-position recovery instead of the
        # row-based anchor heuristic above (which excludes all repeat_group fields).
        nominee_missing = [
            {"path": p, "label": f["label"]}
            for p, f in metas
            if f.get("repeat_group") == "nominee_details" and not f["coded"] and not f.get("readonly")
            and not f.get("answer_field") and "options" not in f
            and flat_human[p] == "NOT_FOUND"
        ]
        if nominee_missing:
            from nominee_table import extract_nominee_table, classify_nominee_missing
            for p, val in extract_nominee_table(nominee_missing, ocr_entries, pdf_path).items():
                flat_human[p] = val
                anchor_paths.add(p)
                notes[p] = "recovered via table-column anchor — verify"
            for p, st in classify_nominee_missing(nominee_missing, ocr_entries, pdf_path).items():
                if flat_human[p] == "NOT_FOUND":
                    state_override[p] = st

        # address_details prints as a composite "Communication/Permanent Address" label
        # (not literal "Address Line 1/2/3" labels), so it needs its own line-splitting
        # recovery instead of the label:value anchor heuristic above.
        address_missing = {
            p for p, f in metas
            if f.get("repeat_group") == "address_details" and p.endswith((".address_line_1", ".address_line_2", ".address_line_3"))
            and flat_human[p] == "NOT_FOUND"
        }
        if address_missing:
            from address_recovery import extract_address_lines
            for p, val in extract_address_lines(ocr_entries).items():
                if p in address_missing:
                    flat_human[p] = val
                    anchor_paths.add(p)
                    notes[p] = "recovered via address-line split — verify"

    omr_paths = set()
    if pdf_path:
        coded_missing = [
            {"path": p, "label": f["label"], "options": f["options"]}
            for p, f in metas
            if f["coded"] and "options" in f and not f.get("repeat_group")
            and not f.get("answer_field") and flat_human[p] == "NOT_FOUND"
        ]
        from checkbox_omr import detect
        for p, text in detect(coded_missing, ocr_entries, pdf_path).items():
            flat_human[p] = text
            omr_paths.add(p)

        # Yes/No tick-matrix OMR — scoped to medical_lifestyle_questions only: that section prints
        # a single "Yes  No" column header once above the numbered questions (verified on a real
        # scan). declaration[] entries don't show that same header signal, so leave them NOT_FOUND
        # rather than guess a column pairing that might not exist for them.
        med_items = fixed_specs.get("medical_lifestyle_questions", {}).get("items", [])
        tick_missing = [
            {"path": p, "label": med_items[int(re.search(r"\[(\d+)\]", p).group(1))]["text"]}
            for p, f in metas
            if f.get("answer_field") and p.startswith("medical_lifestyle_questions[") and flat_human[p] == "NOT_FOUND"
        ]
        from checkbox_omr import detect_ticks
        for p, ans in detect_ticks(tick_missing, ocr_entries, pdf_path).items():
            flat_human[p] = ans
            omr_paths.add(p)

    coded_by_path = {p: f["coded"] for p, f in metas}
    # Guard A — drop suspect-section values that merely echo another section (pass-1 hallucination)
    source_values = {
        _norm(v) for p, v in flat_human.items()
        if v != "NOT_FOUND" and not p.startswith(SUSPECT_SECTIONS) and len(_norm(v)) >= 4
    }
    for p in list(flat_human):
        if flat_human[p] == "NOT_FOUND" or coded_by_path.get(p) or not p.startswith(SUSPECT_SECTIONS):
            continue
        nv = _norm(flat_human[p])
        if len(nv) >= 4 and any(nv in sv or sv in nv for sv in source_values):
            flat_human[p] = "NOT_FOUND"
            notes[p] = "dropped — duplicate of another section"
    # Guard B — a person section with no first name is not a real filled person; null its remaining fields
    for sect in NAME_GATED_SECTIONS:
        if flat_human.get(f"{sect}.first_name", "NOT_FOUND") == "NOT_FOUND":
            for p in list(flat_human):
                if p.startswith(sect + ".") and not coded_by_path.get(p) and flat_human[p] != "NOT_FOUND":
                    flat_human[p] = "NOT_FOUND"
                    notes.setdefault(p, "dropped — section has no name")

    # Part C — classify remaining missing singleton text fields: blank (empty on form) vs no_output (has ink)
    text_missing = [
        {"path": p, "label": f["label"]}
        for p, f in metas
        if not f.get("repeat_group") and not f["coded"] and not f.get("readonly")
        and not f.get("answer_field") and "options" not in f
        and p not in MIRROR_FIELDS
        and flat_human[p] == "NOT_FOUND"
    ]
    if pdf_path and text_missing:
        from anchor_fill import classify_missing
        state_override.update(classify_missing(text_missing, ocr_entries, pdf_path))

    # Mirror duplicate-target fields from their source now that the source has gone through
    # anchor/OMR recovery — single ask, single value, no independent LLM drift between the two.
    for dest, source in MIRROR_FIELDS.items():
        flat_human[dest] = flat_human.get(source, "NOT_FOUND")
        if flat_human[dest] == "NOT_FOUND":
            state_override[dest] = state_override.get(source, "no_output")
        if source in anchor_paths:
            anchor_paths.add(dest)
        if source in notes:
            notes.setdefault(dest, notes[source])

    invalid_paths = set()
    for p, f in metas:
        if f["coded"] or flat_human[p] == "NOT_FOUND":
            continue
        ok, norm, label = validate(p, flat_human[p])
        if ok:
            flat_human[p] = norm
        else:
            # keep the raw extracted value — don't discard real OCR output over a business-rule
            # mismatch (e.g. one OCR-misread PAN char); flag it so the reviewer can eyeball it.
            notes[p] = f"failed {label} check"
            invalid_paths.add(p)

    decoded = _decode(spec, flat_human)

    fields = []
    for p, f in metas:
        human = flat_human[p]
        found = human != "NOT_FOUND"
        if f.get("readonly"):
            conf, low = None, False
        elif f.get("answer_field"):
            conf, low = None, found
        elif (p in anchor_paths or p in omr_paths) and found:
            conf, low = None, True
        else:
            conf = _confidence(human, ocr_entries) if found else None
            low = found and (conf is None or conf < threshold)
        note = notes.get(p)
        if p in anchor_paths and found and not note:
            note = "recovered via anchor — verify"
        if p in omr_paths and found and not note:
            note = "checkbox detected — verify"
        state = "found" if found else state_override.get(p, "no_output")
        item = {
            "path": p,
            "label": f["label"],
            "section": f["section"],
            "coded": f["coded"],
            "state": state,
            "display": human if found else "",
            "value": decoded[p] if found else "",
            "confidence": conf,
            "low": low,
            "invalid": p in invalid_paths,
            "note": note,
        }
        if f.get("readonly"):
            item["readonly"] = True
        if "options" in f:
            item["options"] = f["options"]
        fields.append(item)

    return {
        "threshold": threshold,
        "flat": decoded,
        "template": assemble(decoded),
        "fields": fields,
    }
