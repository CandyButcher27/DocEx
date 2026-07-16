import re

from field_extractor import reading_order


def extract_address_lines(ocr_entries):
    """Recover address_line_1/2/3 for forms that print a single composite
    "Communication/Permanent Address" label followed by a Landmark/State/PIN
    row and a continuation row before the mobile number, instead of literal
    "Address Line 1/2/3" labels (confirmed layout on BPR000513405100.pdf)."""
    pages = reading_order(ocr_entries)
    lines = [l for p in pages for l in p["lines"]]
    result = {}
    for line in lines:
        if re.search(r"communication.*permanent.*address", line, re.I):
            m = re.search(r"address\s*(.*)", line, re.I)
            val = m.group(1).strip(" \t:") if m else ""
            if val:
                result["address_details[0].address_line_1"] = val
        if line.strip().lower().startswith("landmark"):
            m = re.match(r"landmark:?\s*(.*?)\s*state", line, re.I)
            if m:
                val = m.group(1).strip(" \t:")
                if val:
                    result["address_details[0].address_line_2"] = val
        if "mobile no" in line.lower():
            m = re.match(r"(.*?)\s*mobile no", line, re.I)
            if m:
                val = m.group(1).strip(" \t:")
                if val and "state" not in val.lower() and "pin" not in val.lower():
                    result["address_details[0].address_line_3"] = val
    return result
