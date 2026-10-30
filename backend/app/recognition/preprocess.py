import numpy as np

from app.recognition.landmarks import FEATURE_DIM, HAND_POINTS, POSE_POINTS

POSE_END = POSE_POINTS * 3
LEFT_END = POSE_END + HAND_POINTS * 3


def resample_sequence(features: np.ndarray, length: int) -> np.ndarray:
    """Linearly resample a (T, FEATURE_DIM) sequence to exactly `length` frames."""
    if features.ndim != 2 or features.shape[1] != FEATURE_DIM:
        raise ValueError(f"expected shape (T, {FEATURE_DIM}), got {features.shape}")
    if features.shape[0] == 0:
        raise ValueError("sequence has no frames")
    if features.shape[0] == length:
        return features.astype(np.float32)
    src = np.linspace(0.0, 1.0, features.shape[0])
    dst = np.linspace(0.0, 1.0, length)
    out = np.stack([np.interp(dst, src, features[:, i]) for i in range(features.shape[1])], axis=1)
    return out.astype(np.float32)


def hand_missing_mask(features: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Per frame booleans (left_missing, right_missing). A missing hand is an all zero 63 value block (see landmarks.py)."""
    return ~features[:, POSE_END:LEFT_END].any(axis=1), ~features[:, LEFT_END:].any(axis=1)


def fill_hand_gaps(features: np.ndarray, max_gap: int) -> np.ndarray:
    """Linearly interpolate each hand over short gaps of at most `max_gap` missing frames that have a detected hand on both sides.

    Longer gaps and gaps at the start or end stay zero, so a hand that is truly absent is never invented. max_gap 0 changes nothing.
    """
    if max_gap <= 0:
        return features
    out = features.astype(np.float32, copy=True)
    for block, missing in zip(
        (slice(POSE_END, LEFT_END), slice(LEFT_END, FEATURE_DIM)), hand_missing_mask(features)
    ):
        t, n = 0, len(missing)
        while t < n:
            if not missing[t]:
                t += 1
                continue
            end = t
            while end < n and missing[end]:
                end += 1
            if t > 0 and end < n and end - t <= max_gap:
                a, b = out[t - 1, block], out[end, block]
                for i in range(t, end):
                    w = (i - (t - 1)) / (end - (t - 1))
                    out[i, block] = a * (1 - w) + b * w
            t = end
    return out


def prepare_sequence(features: np.ndarray, seq_len: int, max_gap: int = 0) -> np.ndarray:
    """The single preprocessing path shared by training and inference: gap fill, then fixed length resample."""
    return resample_sequence(fill_hand_gaps(features, max_gap), seq_len)
