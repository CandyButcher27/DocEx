import json
import re
from pathlib import Path

from llm_client import run_extraction
from validators import validate

ROOT = Path(__file__).parent
SPEC_FILE = ROOT / "field_spec.json"
CODE_MAPPER_FILE = ROOT / "code_mapper.json"

_spec = None
_mapper = None


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


def _fixed_specs():
    m = load_mapper()
    med = [{"code": o["id"], "text": o["text"]} for o in m["medicalQuestionOptions"] if o["id"].startswith("1000")]
    dec = [{"code": o["code"], "text": o["text"]} for o in m["declaration"]]
    return {
        "medical_lifestyle_questions": {"section": "Medical Questions", "answer_key": "medical_answers", "items": med, "description": True},
        "declaration": {"section": "Declaration", "answer_key": "declaration_answers", "items": dec, "description": False},
    }


def _norm(s):
    return re.sub(r"[^a-z0-9]", "", str(s).lower())


def _trunc(s, n=70):
    s = str(s).replace("\n", " ")
    return s if len(s) <= n else s[: n - 1] + "…"


VARIABLE_GROUPS = ("nominee_details", "address_details")
FIXED_GROUPS = ("medical_lifestyle_questions", "declaration")
SKIP_GROUPS = ("documents", "otp_details")
MAX_INSTANCES = 10
YESNO_OPTIONS = [{"text": "Yes", "value": "Yes"}, {"text": "No", "value": "No"}]


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
        "You are a document field extractor. You are given OCR text from a scanned form as JSON.",
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
    for g, fx in _fixed_specs().items():
        lines.append(f'{fx["section"]} — JSON key "{fx["answer_key"]}" = object mapping each code below to "Yes", "No", or "NOT_FOUND" (the applicant\'s answer/tick in the document):')
        for item in fx["items"]:
            lines.append(f'  - {item["code"]} : {_trunc(item["text"], 90)}')
        lines.append("")
    return "\n".join(lines)


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
    root = {}
    for path, val in flat.items():
        if val == "NOT_FOUND":
            continue
        _set_path(root, path, val)
    return _finalize_fixed(root)


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


def _set_path(root, path, val):
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
            while len(arr) <= idx:
                arr.append({})
            if last:
                arr[idx] = val
            else:
                cur = arr[idx]
    return root


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


def extract(ocr_entries, spec=None, threshold=0.95, pdf_path=None):
    spec = spec or load_spec()
    groups = _group_templates(spec)
    prompt = build_prompt(spec)
    raw = run_extraction({"ocr": ocr_entries}, prompt)
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    try:
        parsed = json.loads(match.group(0)) if match else {}
    except json.JSONDecodeError:
        parsed = {}

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
    for g, fx in _fixed_specs().items():
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
    if pdf_path:
        missing = [
            {"path": p, "label": f["label"]}
            for p, f in metas
            if not f.get("repeat_group") and not f["coded"] and not f.get("readonly")
            and not f.get("answer_field") and "options" not in f
            and flat_human[p] == "NOT_FOUND"
        ]
        from anchor_fill import anchor_fill
        all_labels = [f["label"] for f in spec["fields"]]
        recovered = anchor_fill(missing, ocr_entries, pdf_path, all_labels)
        for p, val in recovered.items():
            flat_human[p] = val
            anchor_paths.add(p)

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

    notes = {}
    for p, f in metas:
        if f["coded"] or flat_human[p] == "NOT_FOUND":
            continue
        ok, norm, label = validate(p, flat_human[p])
        if ok:
            flat_human[p] = norm
        else:
            flat_human[p] = "NOT_FOUND"
            notes[p] = f"failed {label} check"

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
        item = {
            "path": p,
            "label": f["label"],
            "section": f["section"],
            "coded": f["coded"],
            "state": "found" if found else "no_output",
            "display": human if found else "",
            "value": decoded[p] if found else "",
            "confidence": conf,
            "low": low,
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
