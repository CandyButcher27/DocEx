import cv2
import numpy as np


def make_page(seed: int = 0, width: int = 850, height: int = 1100) -> np.ndarray:
    rng = np.random.default_rng(seed)
    image = np.full((height, width, 3), 255, dtype=np.uint8)

    for i in range(40):
        x = int(rng.integers(20, width - 120))
        y = int(rng.integers(20, height - 60))
        cv2.rectangle(image, (x, y), (x + 90, y + 30), (0, 0, 0), 1)
        cv2.putText(image, f"F{i:02d}", (x + 5, y + 22), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 1)

    for _ in range(60):
        x = int(rng.integers(0, width))
        y = int(rng.integers(0, height))
        cv2.circle(image, (x, y), 2, (0, 0, 0), -1)

    return image
