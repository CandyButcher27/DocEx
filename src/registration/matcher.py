from dataclasses import dataclass

import cv2
import numpy as np

from src.template.enums import RegistrationMethod


@dataclass(frozen=True, slots=True)
class MatchResult:
    score: float
    num_inliers: int
    num_matches: int
    homography: np.ndarray | None


def _detector(method: RegistrationMethod):
    if method == RegistrationMethod.ORB:
        return cv2.ORB_create(nfeatures=2000), cv2.NORM_HAMMING
    if method == RegistrationMethod.AKAZE:
        return cv2.AKAZE_create(), cv2.NORM_HAMMING
    if method == RegistrationMethod.SIFT:
        return cv2.SIFT_create(), cv2.NORM_L2
    raise ValueError(f"Unsupported registration method for feature matching: {method}.")


def _to_gray(image: np.ndarray) -> np.ndarray:
    return image if image.ndim == 2 else cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)


def match_images(page: np.ndarray, reference: np.ndarray, method: RegistrationMethod) -> MatchResult:
    detector, norm = _detector(method)

    page_gray = _to_gray(page)
    ref_gray = _to_gray(reference)

    kp1, des1 = detector.detectAndCompute(page_gray, None)
    kp2, des2 = detector.detectAndCompute(ref_gray, None)

    if des1 is None or des2 is None or len(kp1) < 4 or len(kp2) < 4:
        return MatchResult(score=0.0, num_inliers=0, num_matches=0, homography=None)

    matcher = cv2.BFMatcher(norm)
    raw = matcher.knnMatch(des1, des2, k=2)
    good = [m for pair in raw if len(pair) == 2 for m, n in [pair] if m.distance < 0.75 * n.distance]

    if len(good) < 4:
        return MatchResult(score=0.0, num_inliers=0, num_matches=len(good), homography=None)

    src_pts = np.float32([kp1[m.queryIdx].pt for m in good]).reshape(-1, 1, 2)
    dst_pts = np.float32([kp2[m.trainIdx].pt for m in good]).reshape(-1, 1, 2)
    homography, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 5.0)

    if homography is None or mask is None:
        return MatchResult(score=0.0, num_inliers=0, num_matches=len(good), homography=None)

    num_inliers = int(mask.sum())
    score = num_inliers / len(good)

    return MatchResult(score=score, num_inliers=num_inliers, num_matches=len(good), homography=homography)
