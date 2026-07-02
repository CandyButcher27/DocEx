import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ocr_engine import run_ocr_on_pdf
from field_extractor import extract

sys.stdout.reconfigure(encoding="utf-8")
pdf = sys.argv[1]

t0 = time.time()
ocr = run_ocr_on_pdf(pdf)
t1 = time.time()
print(f"OCR: {len(ocr)} lines, {t1 - t0:.1f}s")

result = extract(ocr, pdf_path=pdf)
t2 = time.time()
print(f"LLM+anchor+assemble: {t2 - t1:.1f}s")

fields = result["fields"]
found = [f for f in fields if f["state"] == "found"]
low = [f for f in found if f["low"]]
anchored = [f for f in found if f["note"] and "anchor" in f["note"]]
notes = [f for f in fields if f["note"]]
print(f"fields={len(fields)} found={len(found)} low_conf={len(low)} anchored={len(anchored)}")
print("=== anchor-recovered ===")
for f in anchored:
    print(f"  {f['path']} = {f['display']!r}")
print("=== notes ===")
for f in notes:
    print(f"  {f['path']}: {f['note']}")

json.dump(result["template"], open("test_output.json", "w", encoding="utf-8"), indent=2, ensure_ascii=False)
print("=== TEMPLATE ===")
print(json.dumps(result["template"], indent=2, ensure_ascii=False))
