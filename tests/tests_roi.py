from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.models.roi import ROI  # Since we had named our class as ROI over there, we are importing that over here


def test_valid_roi():
    roi = ROI(0.1, 0.2, 0.3, 0.4)

    assert roi.right == 0.4
    assert roi.bottom == 0.6


def test_pixel_conversion():
    roi = ROI(0.5, 0.25, 0.1, 0.2)

    assert roi.to_pixels(1000, 2000) == (
        500,
        500,
        100,
        400,
    )


def test_invalid_roi():
    import pytest

    with pytest.raises(ValueError):
        ROI(1.2, 0.0, 0.2, 0.2)


def test_roi_outside_page():
    import pytest

    with pytest.raises(ValueError):
        ROI(0.9, 0.5, 0.2, 0.2)