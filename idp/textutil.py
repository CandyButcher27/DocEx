from __future__ import annotations

import re
from difflib import SequenceMatcher

_norm_re = re.compile(r"[^a-z0-9]+")


def normalize(s: str) -> str:
    return _norm_re.sub("", s.lower())


def normalize_tokens(s: str) -> list[str]:
    return [t for t in re.split(r"[^a-z0-9]+", s.lower()) if t]


def similarity(a: str, b: str) -> float:
    na, nb = normalize(a), normalize(b)
    if not na or not nb:
        return 0.0
    return SequenceMatcher(None, na, nb).ratio()


def contains_ratio(needle: str, haystack: str) -> float:
    n, h = normalize(needle), normalize(haystack)
    if not n or not h:
        return 0.0
    if n in h:
        return 1.0
    ln = len(n)
    best = 0.0
    step = max(1, ln // 4)
    for i in range(0, max(1, len(h) - ln + 1), step):
        window = h[i:i + ln]
        r = SequenceMatcher(None, n, window).ratio()
        if r > best:
            best = r
            if best == 1.0:
                break
    return best
