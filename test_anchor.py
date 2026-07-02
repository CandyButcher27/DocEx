import json
import os
import sys
import time

from ocr_engine import run_ocr_on_pdf
from field_extractor import extract

sys.stdout.reconfigure(encoding="utf-8")
pdf = sys.argv[1]
cache = os.path.splitext(os.path.basename(pdf))[0] + ".ocrcache.json"

if os.path.exists(cache):
    ocr = json.load(open(cache, encoding="utf-8"))
    print(f"OCR: {len(ocr)} lines (cached)")
else:
    t0 = time.time()
    ocr = run_ocr_on_pdf(pdf)
    json.dump(ocr, open(cache, "w", encoding="utf-8"))
    print(f"OCR: {len(ocr)} lines, {time.time() - t0:.1f}s (cached to {cache})")

t = time.time()
res = extract(ocr, pdf_path=pdf)
print(f"extract (pass1 + anchor): {time.time() - t:.1f}s\n")

fields = res["fields"]
found = [f for f in fields if f["state"] == "found"]
anchored = [f for f in found if f["note"] and "anchor" in f["note"]]
omr = [f for f in found if f["note"] and "checkbox" in f["note"]]
still_missing = [
    f for f in fields
    if f["state"] == "no_output" and not f["coded"]
    and "options" not in f and not f.get("readonly")
]

print(f"pass1 found: {len(found) - len(anchored) - len(omr)}   +anchor: {len(anchored)}   +checkbox: {len(omr)}   total found: {len(found)}\n")
print(f"=== anchor recovered ({len(anchored)}) ===")
for f in anchored:
    print(f"  {f['path']} = {f['display']!r}")
print(f"\n=== checkbox recovered ({len(omr)}) ===")
for f in omr:
    print(f"  {f['path']} = {f['display']!r} -> {f['value']}")
print(f"\n=== still NO OUTPUT text fields ({len(still_missing)}) — anchor gap ===")
for f in still_missing:
    print(f"  {f['path']}  ({f['label']})")

json.dump(res["template"], open("test_output.json", "w", encoding="utf-8"), indent=2, ensure_ascii=False)
print("\nwrote test_output.json")
