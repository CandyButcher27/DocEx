import numpy as np

from src.roi.cropper import crop_roi
from src.template.roi_config import ROIConfig


def test_crop_roi_returns_subregion():
    image = np.arange(100 * 100, dtype=np.uint8).reshape(100, 100)
    roi = ROIConfig(x=0.1, y=0.2, width=0.3, height=0.4)
    crop = crop_roi(image, roi)
    assert crop is not None
    assert crop.shape == (40, 30)


def test_crop_roi_none_coords_returns_none():
    image = np.zeros((50, 50), dtype=np.uint8)
    roi = ROIConfig(x=None, y=None, width=None, height=None)
    assert crop_roi(image, roi) is None


def test_crop_roi_zero_area_returns_none():
    image = np.zeros((50, 50), dtype=np.uint8)
    roi = ROIConfig(x=0.5, y=0.5, width=0.0, height=0.0)
    assert crop_roi(image, roi) is None
