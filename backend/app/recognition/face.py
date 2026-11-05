"""Face landmark block: eyebrows, eyes and mouth only (50 of the 468 MediaPipe Holistic face points), as a separate feature block.

The block is normalized exactly like the body features (shoulder midpoint as origin, shoulder width as scale, from the same frame's pose),
so training (Python MediaPipe on video) and live use (browser MediaPipe) share this one code path. A frame without a face is all zeros.
The browser sends the 50 selected points in FACE_INDICES order (frontend/src/lib/faceIndices.ts must list the same numbers).
"""

import math

import numpy as np

from app.schemas.landmarks import LandmarkFrame, Point

LEFT_BROW = (70, 63, 105, 66, 107)
RIGHT_BROW = (300, 293, 334, 296, 336)
LEFT_EYE = (33, 160, 158, 133, 153, 144)
RIGHT_EYE = (362, 385, 387, 263, 373, 380)
MOUTH_OUTER = (61, 146, 91, 181, 84, 17, 314, 405, 321, 375, 291, 409, 270, 269, 267, 0, 37, 39, 40, 185)
MOUTH_INNER = (78, 81, 13, 311, 308, 402, 14, 178)
FACE_INDICES: tuple[int, ...] = LEFT_BROW + RIGHT_BROW + LEFT_EYE + RIGHT_EYE + MOUTH_OUTER + MOUTH_INNER
FACE_POINTS = len(FACE_INDICES)  # 50
FACE_DIM = FACE_POINTS * 3
FULL_FACE_POINTS = 468
LEFT_SHOULDER, RIGHT_SHOULDER = 11, 12
MIN_SHOULDER_WIDTH = 1e-3


def select_face(full: list[Point] | None) -> list[Point] | None:
    """The 50 selected points from the full 468 point face mesh (None when the face was not detected)."""
    if full is None or len(full) != FULL_FACE_POINTS:
        return None
    return [full[i] for i in FACE_INDICES]


def face_block(frame: LandmarkFrame) -> np.ndarray:
    """(FACE_DIM,) float32 block for one frame; zeros when the pose cannot normalize it or the face is missing or malformed."""
    zeros = np.zeros(FACE_DIM, dtype=np.float32)
    if not frame.pose or len(frame.pose) != 33 or not frame.face or len(frame.face) != FACE_POINTS:
        return zeros
    pose = np.array([[p.x, p.y, p.z] for p in frame.pose], dtype=np.float64)
    face = np.array([[p.x, p.y, p.z] for p in frame.face], dtype=np.float64)
    if not (np.isfinite(pose).all() and np.isfinite(face).all()):
        return zeros
    origin = (pose[LEFT_SHOULDER] + pose[RIGHT_SHOULDER]) / 2
    scale = float(np.linalg.norm(pose[LEFT_SHOULDER, :2] - pose[RIGHT_SHOULDER, :2]))
    if not math.isfinite(scale) or scale < MIN_SHOULDER_WIDTH:
        return zeros
    return ((face - origin) / scale).reshape(-1).astype(np.float32)


def resample_block(block: np.ndarray, length: int) -> np.ndarray:
    """Linearly resample a (T, D) block to `length` frames (the same rule as app.recognition.preprocess.resample_sequence, any width)."""
    t = block.shape[0]
    if t == length:
        return block.astype(np.float32)
    if t == 1:
        return np.repeat(block, length, axis=0).astype(np.float32)
    pos = np.linspace(0.0, 1.0, length) * (t - 1)
    i0 = np.minimum(np.floor(pos).astype(np.int64), t - 2)
    w = (pos - i0)[:, None]
    return (block[i0].astype(np.float64) * (1.0 - w) + block[i0 + 1].astype(np.float64) * w).astype(np.float32)
