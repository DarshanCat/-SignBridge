"""Landmark validation and normalization.

Feature format (per frame, FEATURE_DIM = 225):
    pose (33 x 3) | left hand (21 x 3) | right hand (21 x 3), each landmark as (x, y, z).
Coordinates are translated so the shoulder midpoint is the origin and divided by the shoulder
width, which removes camera position and signer distance. A missing hand is all zeros (the
hand-presence flags are reported separately). A frame without a usable pose is invalid: it cannot
be normalized, so its feature row is all zeros and it is excluded from `valid_frames`.
"""

import math

import numpy as np

from app.schemas.landmarks import (
    FrameReport,
    LandmarkFrame,
    LandmarkSequenceRequest,
    LandmarkSequenceResponse,
    Point,
)

POSE_POINTS = 33
HAND_POINTS = 21
LEFT_SHOULDER, RIGHT_SHOULDER = 11, 12
FEATURE_DIM = (POSE_POINTS + 2 * HAND_POINTS) * 3
MIN_SHOULDER_WIDTH = 1e-3
MIN_VALID_FRAMES = 8
MIN_HAND_FRAMES = 4


def _to_array(points: list[Point], expected: int, name: str, issues: list[str]) -> np.ndarray | None:
    if len(points) != expected:
        issues.append(f"{name}: expected {expected} landmarks, got {len(points)}")
        return None
    arr = np.array([[p.x, p.y, p.z] for p in points], dtype=np.float64)
    if not np.isfinite(arr).all():
        issues.append(f"{name}: contains non-finite values")
        return None
    return arr


def normalize_frame(frame: LandmarkFrame) -> tuple[np.ndarray, FrameReport]:
    issues: list[str] = []
    zeros = np.zeros(FEATURE_DIM, dtype=np.float32)

    pose = _to_array(frame.pose, POSE_POINTS, "pose", issues) if frame.pose else None
    if pose is None:
        if frame.pose is None:
            issues.append("pose: missing")
        return zeros, FrameReport(valid=False, has_left_hand=False, has_right_hand=False, issues=issues)

    origin = (pose[LEFT_SHOULDER] + pose[RIGHT_SHOULDER]) / 2
    scale = float(np.linalg.norm(pose[LEFT_SHOULDER, :2] - pose[RIGHT_SHOULDER, :2]))
    if not math.isfinite(scale) or scale < MIN_SHOULDER_WIDTH:
        issues.append("pose: shoulders too close together to normalize")
        return zeros, FrameReport(valid=False, has_left_hand=False, has_right_hand=False, issues=issues)

    def norm(a: np.ndarray) -> np.ndarray:
        return ((a - origin) / scale).reshape(-1)

    parts = [norm(pose)]
    present: list[bool] = []
    for name, pts in (("left_hand", frame.left_hand), ("right_hand", frame.right_hand)):
        arr = _to_array(pts, HAND_POINTS, name, issues) if pts else None
        present.append(arr is not None)
        parts.append(norm(arr) if arr is not None else np.zeros(HAND_POINTS * 3))

    features = np.concatenate(parts).astype(np.float32)
    return features, FrameReport(
        valid=True, has_left_hand=present[0], has_right_hand=present[1], issues=issues
    )


def process_sequence(req: LandmarkSequenceRequest) -> LandmarkSequenceResponse:
    rows, reports = zip(*(normalize_frame(f) for f in req.frames))
    valid = sum(r.valid for r in reports)
    with_hands = sum(r.valid and (r.has_left_hand or r.has_right_hand) for r in reports)

    warnings: list[str] = []
    if valid < MIN_VALID_FRAMES:
        warnings.append(f"Only {valid} valid frame(s); at least {MIN_VALID_FRAMES} are needed.")
    if with_hands < MIN_HAND_FRAMES:
        warnings.append(f"Hands visible in only {with_hands} frame(s); at least {MIN_HAND_FRAMES} are needed.")

    return LandmarkSequenceResponse(
        num_frames=len(rows),
        feature_dim=FEATURE_DIM,
        valid_frames=valid,
        frames_with_hands=with_hands,
        usable=not warnings,
        warnings=warnings,
        frame_reports=list(reports),
        features=[r.tolist() for r in rows],
    )
