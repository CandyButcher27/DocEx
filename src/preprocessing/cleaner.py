import cv2
import numpy as np

from src.template.preprocessing_config import PreprocessingConfig


def to_grayscale(image: np.ndarray) -> np.ndarray:
    if image.ndim == 2:
        return image
    return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)


def estimate_skew_angle(gray: np.ndarray) -> float:
    inverted = cv2.bitwise_not(gray)
    threshold = cv2.threshold(inverted, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]
    coords = np.column_stack(np.where(threshold > 0))

    if coords.shape[0] < 10:
        return 0.0

    angle = cv2.minAreaRect(coords)[-1]
    if angle < -45:
        angle = 90 + angle
    return -angle


def deskew(image: np.ndarray) -> np.ndarray:
    gray = to_grayscale(image)
    angle = estimate_skew_angle(gray)

    if abs(angle) < 0.1:
        return image

    h, w = image.shape[:2]
    matrix = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1.0)
    return cv2.warpAffine(image, matrix, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)


def denoise(image: np.ndarray) -> np.ndarray:
    if image.ndim == 2:
        return cv2.fastNlMeansDenoising(image, h=10)
    return cv2.fastNlMeansDenoisingColored(image, h=10)


def enhance_contrast(image: np.ndarray) -> np.ndarray:
    gray = to_grayscale(image)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    return clahe.apply(gray)


def adaptive_threshold(image: np.ndarray) -> np.ndarray:
    gray = to_grayscale(image)
    return cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, blockSize=31, C=15
    )


def clean_image(image: np.ndarray, config: PreprocessingConfig) -> np.ndarray:
    result = image

    if config.deskew:
        result = deskew(result)

    if config.denoise:
        result = denoise(result)

    if config.contrast_enhancement:
        result = enhance_contrast(result)

    if config.adaptive_threshold:
        result = adaptive_threshold(result)

    return result
