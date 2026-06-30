import base64

import cv2
import numpy as np


def encode_png_b64(image: np.ndarray) -> str:
    ok, buffer = cv2.imencode(".png", image)
    if not ok:
        raise ValueError("Failed to PNG-encode image for VLM request.")
    return base64.b64encode(buffer.tobytes()).decode("ascii")
