import cv2
import numpy as np


def align_to_reference(
    page: np.ndarray,
    reference: np.ndarray,
    homography: np.ndarray,
) -> np.ndarray:
    h, w = reference.shape[:2]
    return cv2.warpPerspective(page, homography, (w, h), flags=cv2.INTER_CUBIC)
