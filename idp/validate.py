from __future__ import annotations

import re

from .models import FieldSpec

PAN_RE = re.compile(r"[A-Z]{5}[0-9]{4}[A-Z]")
DATE_RE = re.compile(r"(\d{1,2})[\s./-]*(\d{1,2})[\s./-]*(\d{2,4})")


def _clean_common(v: str) -> str:
    return re.sub(r"\s+", " ", v).strip()


def validate_field(spec: FieldSpec, value: str) -> tuple[bool, str, str]:
    v = _clean_common(value)
    if not v:
        return (not spec.required, v, "empty" if spec.required else "")

    if spec.max_len and len(v) > spec.max_len:
        return False, v, f"exceeds max_len {spec.max_len}"

    if spec.datatype == "pan":
        cand = re.sub(r"[^A-Za-z0-9]", "", v).upper()
        m = PAN_RE.search(cand)
        if m:
            return True, m.group(0), ""
        return False, cand, "invalid PAN format"

    if spec.datatype == "number":
        cand = re.sub(r"[^0-9]", "", v)
        alnum = re.sub(r"[^A-Za-z0-9]", "", v)
        if not cand:
            return False, v, "no digits"
        if alnum and len(cand) / len(alnum) < 0.6:
            return False, v, "digits embedded in text"
        return True, cand, ""

    if spec.datatype == "date":
        m = DATE_RE.search(v)
        if m:
            d, mo, y = m.groups()
            if len(y) == 2:
                y = "20" + y
            if 1 <= int(d) <= 31 and 1 <= int(mo) <= 12:
                return True, f"{int(d):02d}-{int(mo):02d}-{y}", ""
            return False, v, "date out of range"
        return False, v, "unparseable date"

    if spec.datatype == "choice" and spec.choices:
        low = v.lower()
        for c in spec.choices:
            if c.lower() in low or low in c.lower():
                return True, c, ""
        return False, v, "not a valid choice"

    if spec.regex:
        m = re.search(spec.regex, v)
        if m:
            return True, m.group(0), ""
        return False, v, "regex mismatch"

    return True, v, ""
