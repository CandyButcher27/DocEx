from __future__ import annotations

import cv2
import numpy as np


def dhash(image: np.ndarray, size: int = 16) -> str:
    g = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if image.ndim == 3 else image
    small = cv2.resize(g, (size + 1, size))
    diff = small[:, 1:] > small[:, :-1]
    bits = diff.flatten()
    val = 0
    for b in bits:
        val = (val << 1) | int(b)
    return format(val, f"0{len(bits) // 4}x")


def hamming(a: str, b: str) -> int:
    if not a or not b or len(a) != len(b):
        return 10 ** 6
    return bin(int(a, 16) ^ int(b, 16)).count("1")
