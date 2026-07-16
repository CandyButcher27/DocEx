import sys, json
from ocr_engine import run_ocr_on_pdf
import ingest_gate as ig

files = [
    "scanned_docs/924030061722211.pdf",
    "scanned_docs/925060052530917.pdf",
    "scanned_docs/BPR000513405100.pdf",
    "scanned_docs/PPR005312996838.pdf",
    "scanned_docs/021784600001417-HDF.pdf",
]

results = {}
for f in files:
    ocr = run_ocr_on_pdf(f)
    n_pages = max(e.get("page",0) for e in ocr) + 1
    texts = ig._page_texts(ocr, n_pages)
    m = ig.match_template(texts)
    results[f] = {"doc_kind": m["doc_kind"], "doc_score": m["doc_score"]}
    print(f, "->", m["doc_kind"], m["doc_score"], flush=True)

with open("scratch_classify_results.json", "w") as out:
    json.dump(results, out, indent=2)
