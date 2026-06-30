import numpy as np

from src.preprocessing.cleaner import adaptive_threshold, clean_image, deskew, to_grayscale
from src.template.preprocessing_config import PreprocessingConfig
from synthetic import make_page


def test_to_grayscale_reduces_channels():
    color = make_page(seed=1)
    gray = to_grayscale(color)
    assert gray.ndim == 2


def test_adaptive_threshold_binary():
    gray = to_grayscale(make_page(seed=2))
    binary = adaptive_threshold(gray)
    assert set(np.unique(binary)).issubset({0, 255})


def test_deskew_returns_same_shape():
    image = make_page(seed=3)
    result = deskew(image)
    assert result.shape == image.shape


def test_clean_image_full_pipeline_runs():
    image = make_page(seed=4)
    config = PreprocessingConfig(
        deskew=True,
        perspective_correction=False,
        adaptive_threshold=True,
        denoise=True,
        contrast_enhancement=True,
    )
    result = clean_image(image, config)
    assert result.ndim == 2
    assert result.shape[0] > 0 and result.shape[1] > 0
