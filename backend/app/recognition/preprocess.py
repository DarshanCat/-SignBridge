import numpy as np

from app.recognition.landmarks import FEATURE_DIM


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
