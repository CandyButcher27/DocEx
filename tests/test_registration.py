import numpy as np

from src.registration.aligner import align_to_reference
from src.registration.matcher import match_images
from src.template.enums import RegistrationMethod
from synthetic import make_page


def test_identical_images_match_strongly():
    page = make_page(seed=10)
    result = match_images(page, page.copy(), RegistrationMethod.ORB)
    assert result.homography is not None
    assert result.num_inliers >= 12
    assert result.score >= 0.18


def test_different_images_match_weakly():
    a = make_page(seed=11)
    b = make_page(seed=999)
    result = match_images(a, b, RegistrationMethod.ORB)
    assert result.score < 0.18


def test_align_returns_reference_size():
    page = make_page(seed=12)
    result = match_images(page, page.copy(), RegistrationMethod.ORB)
    aligned = align_to_reference(page, page.copy(), result.homography)
    assert aligned.shape[:2] == page.shape[:2]
