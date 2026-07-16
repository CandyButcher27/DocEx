import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ocr_engine import run_ocr_on_pdf
from field_extractor import extract
import ingest_gate
import doc_type_registry

sys.stdout.reconfigure(encoding="utf-8")

pdf = sys.argv[1]
page_number = int(sys.argv[2])  # 1-indexed, matches how a reviewer counts pages
doc_kind_override = sys.argv[3] if len(sys.argv) > 3 else None

cache = os.path.splitext(os.path.basename(pdf))[0] + ".ocrcache.json"
if os.path.exists(cache):
    ocr = json.load(open(cache, encoding="utf-8"))
else:
    ocr = run_ocr_on_pdf(pdf)
    json.dump(ocr, open(cache, "w", encoding="utf-8"))

page_idx = page_number - 1
page_ocr = [e for e in ocr if e.get("page", 0) == page_idx]
print(f"page {page_number}: {len(page_ocr)} OCR entries (of {len(ocr)} total)")

if doc_kind_override:
    doc_kind = doc_kind_override
else:
    page_texts = [" ".join(e["text"] for e in page_ocr)]
    match = ingest_gate.match_template(page_texts)
    doc_kind = match["doc_kind"]
print(f"doc_kind: {doc_kind}")

config = doc_type_registry.resolve(doc_kind)
spec = config["spec"] if config else None

result = extract(page_ocr, spec=spec, pdf_path=pdf, doc_type=doc_kind)

fields = result["fields"]
found = [f for f in fields if f["state"] == "found"]
low = [f for f in found if f["low"]]
anchored = [f for f in found if f["note"] and "anchor" in f["note"]]
missing = [f for f in fields if f["state"] != "found"]

print(f"fields={len(fields)} found={len(found)} low_conf={len(low)} anchored={len(anchored)}")
print("=== found on this page ===")
for f in found:
    flag = " [LOW]" if f["low"] else ""
    print(f"  {f['path']} = {f['display']!r}{flag}")
print("=== still missing (state != found) ===")
for f in missing:
    print(f"  {f['path']}: {f['state']}")
