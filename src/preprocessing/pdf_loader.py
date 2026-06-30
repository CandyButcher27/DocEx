from pathlib import Path

import cv2
import numpy as np
from pdf2image import convert_from_path


def pdf_to_images(pdf_path: str | Path, dpi: int = 300, poppler_path: str = "") -> list[np.ndarray]:
    kwargs = {"dpi": dpi}
    if poppler_path:
        kwargs["poppler_path"] = poppler_path

    pil_pages = convert_from_path(str(pdf_path), **kwargs)
    return [cv2.cvtColor(np.array(page), cv2.COLOR_RGB2BGR) for page in pil_pages]
