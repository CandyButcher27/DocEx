import json
import math
import os
import re
import sys
from collections import Counter

import cv2
import numpy as np

from ocr_engine import render_pages, run_ocr_on_pdf

ROOT = os.path.dirname(os.path.abspath(__file__))
STORE_FILE = os.path.join(ROOT, "data", "template_store.json")

BLUR_THRESH = 100.0        # variance-of-Laplacian below this = too blurred
MATCH_THRESH = 0.25        # doc-level best cosine below this = unrecognized form
BLUR_MAX_SIDE = 1500       # downscale long side before sharpness measure (resolution-normalize)

# DOB deferred: insured date_of_birth is absent from the source schema (field_spec) so the
# pipeline can't extract it yet. Add insured_details.date_of_birth to the spec to re-enable.
MANDATORY = [
    "insured_details.first_name",
    "insured_details.pan_number",
]

_store = None


def _tokens(s):
    return [t for t in re.sub(r"[^a-z0-9]", " ", str(s).lower()).split() if len(t) >= 2]


def load_store():
    global _store
    if _store is None:
        with open(STORE_FILE, encoding="utf-8") as f:
            _store = json.load(f)
    return _store


def _vectorize(text, store):
    vocab, idf = store["vocab"], store["idf"]
    counts = Counter(t for t in _tokens(text) if t in vocab)
    vec = np.zeros(len(vocab))
    for tok, n in counts.items():
        i = vocab[tok]
        vec[i] = (1.0 + math.log(n)) * idf[i]
    norm = np.linalg.norm(vec)
    return vec / norm if norm else vec


def _page_texts(ocr_entries, n_pages):
    texts = [""] * n_pages
    buckets = {}
    for e in ocr_entries:
        buckets.setdefault(e.get("page", 0), []).append(e.get("text", ""))
    for p, parts in buckets.items():
        if 0 <= p < n_pages:
            texts[p] = " ".join(parts)
    return texts


def match_template(page_texts, store=None):
    store = store or load_store()
    mats = [np.array(d["vec"]) for d in store["docs"]]
    names = [d["name"] for d in store["docs"]]
    per_page = []
    for text in page_texts:
        v = _vectorize(text, store)
        scores = [float(v @ m) for m in mats]
        j = int(np.argmax(scores))
        per_page.append({"kind": names[j], "score": scores[j], "all": dict(zip(names, scores))})
    best = max(per_page, key=lambda x: x["score"]) if per_page else {"kind": None, "score": 0.0}
    return {"doc_kind": best["kind"], "doc_score": best["score"], "pages": per_page}


def _sharpness(pil_img):
    g = np.array(pil_img.convert("L"))
    h, w = g.shape
    scale = BLUR_MAX_SIDE / max(h, w)
    if scale < 1.0:
        g = cv2.resize(g, (int(w * scale), int(h * scale)))
    return float(cv2.Laplacian(g, cv2.CV_64F).var())


def check_blur(pages):
    vals = [_sharpness(p) for p in pages]
    worst = min(vals) if vals else 0.0
    return worst >= BLUR_THRESH, {"page_sharpness": vals, "worst": worst}


def check_mandatory(fields):
    by_path = {f["path"]: f for f in fields}
    missing = [
        by_path.get(p, {}).get("label", p.rsplit(".", 1)[-1])
        for p in MANDATORY
        if by_path.get(p, {}).get("state") != "found"
    ]
    return not missing, {"missing": missing}


def check(pdf_path, ocr_entries=None):
    """Pre-extraction gate. Returns {ok, reason, detail, ocr}."""
    pages = render_pages(pdf_path)
    detail = {}

    ok, blur = check_blur(pages)
    detail["blur"] = blur
    if not ok:
        return {"ok": False, "reason": "blurred — please reupload a clearer scan", "detail": detail, "ocr": ocr_entries}

    if ocr_entries is None:
        ocr_entries = run_ocr_on_pdf(pdf_path)

    match = match_template(_page_texts(ocr_entries, len(pages)))
    detail["match"] = match
    if match["doc_score"] < MATCH_THRESH:
        return {"ok": False, "reason": "unrecognized form — does not match any known template", "detail": detail, "ocr": ocr_entries}

    return {"ok": True, "reason": None, "detail": detail, "ocr": ocr_entries}


def _calibrate(pdf_glob):
    import glob
    store = load_store()
    names = [d["name"] for d in store["docs"]]
    print("template x template cosine (self should dominate its row):")
    mats = [np.array(d["vec"]) for d in store["docs"]]
    print(f"{'':22}" + "".join(f"{n[:14]:>16}" for n in names))
    for i, d in enumerate(store["docs"]):
        row = "".join(f"{float(np.array(d['vec']) @ m):>16.3f}" for m in mats)
        print(f"{d['name'][:22]:22}{row}")
    print("\nfile  ->  sharpness(min) | best template (score) | per-page kinds")
    for path in sorted(glob.glob(pdf_glob)):
        pages = render_pages(path)
        sh = [round(_sharpness(p), 1) for p in pages]
        ocr = run_ocr_on_pdf(path)
        m = match_template(_page_texts(ocr, len(pages)))
        pk = [(p["kind"][:16], round(p["score"], 3)) for p in m["pages"]]
        print(f"{os.path.basename(path):34} sh_min={min(sh):8.1f}  {m['doc_kind'][:20]:22} {m['doc_score']:.3f}  {pk}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    if len(sys.argv) >= 3 and sys.argv[1] == "--calibrate":
        _calibrate(sys.argv[2])
    else:
        r = check(sys.argv[1])
        print(json.dumps({k: v for k, v in r.items() if k != "ocr"}, indent=2, ensure_ascii=False))
