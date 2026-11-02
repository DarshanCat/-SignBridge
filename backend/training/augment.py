"""Landmark sequence augmentation (training only). Operates on normalized (T, 225) features, never on images.

All transforms are linear about the shoulder-midpoint origin or act on the time axis, so an all zero (missing) hand block stays
zero under rotation and scaling. Every random choice comes from the supplied numpy Generator, so runs are reproducible.
"""

from dataclasses import dataclass

import numpy as np

from app.recognition.landmarks import FEATURE_DIM
from app.recognition.preprocess import resample_sequence


@dataclass(frozen=True)
class AugmentConfig:
    max_rotation_deg: float = 10.0  # rotation in the image (x, y) plane
    scale_range: tuple[float, float] = (0.9, 1.1)
    speed_range: tuple[float, float] = (0.8, 1.2)  # >1 means faster signing (shorter sequence)
    jitter_frac: float = 0.05  # per frame timing noise as a fraction of the sequence length
    crop_frac: float = 0.1  # at most this fraction trimmed from each end
    p_rotate: float = 0.8
    p_scale: float = 0.8
    p_speed: float = 0.8
    p_jitter: float = 0.5


def rotate_xy(x: np.ndarray, degrees: float) -> np.ndarray:
    """Rotate every landmark's (x, y) by `degrees`; z is unchanged. Layout: 75 landmarks of (x, y, z)."""
    a = np.deg2rad(degrees)
    c, s = np.cos(a), np.sin(a)
    out = x.copy().reshape(x.shape[0], -1, 3)
    px, py = out[..., 0].copy(), out[..., 1].copy()
    out[..., 0] = c * px - s * py
    out[..., 1] = s * px + c * py
    return out.reshape(x.shape)


def speed_resample(x: np.ndarray, factor: float) -> np.ndarray:
    """Change the signing speed: new length = round(T / factor), at least 4 frames."""
    new_len = max(4, int(round(x.shape[0] / factor)))
    return resample_sequence(x, new_len)


def time_jitter(x: np.ndarray, rng: np.random.Generator, cfg: AugmentConfig) -> np.ndarray:
    """Resample at slightly perturbed, still ordered time points and trim a few frames at each end."""
    t = x.shape[0]
    lo = int(rng.integers(0, int(t * cfg.crop_frac) + 1))
    hi = t - int(rng.integers(0, int(t * cfg.crop_frac) + 1))
    if hi - lo < 4:
        lo, hi = 0, t
    pts = np.linspace(lo, hi - 1, t) + rng.normal(0, cfg.jitter_frac * t, size=t)
    pts = np.clip(np.sort(pts), 0, t - 1)
    src = np.arange(t)
    return np.stack([np.interp(pts, src, x[:, i]) for i in range(x.shape[1])], axis=1).astype(np.float32)


def augment_sequence(x: np.ndarray, rng: np.random.Generator, cfg: AugmentConfig | None = None) -> np.ndarray:
    cfg = cfg or AugmentConfig()
    if x.ndim != 2 or x.shape[1] != FEATURE_DIM:
        raise ValueError(f"expected shape (T, {FEATURE_DIM}), got {x.shape}")
    out = x.astype(np.float32, copy=True)
    if rng.random() < cfg.p_speed:
        out = speed_resample(out, float(rng.uniform(*cfg.speed_range)))
    if rng.random() < cfg.p_jitter and out.shape[0] >= 8:
        out = time_jitter(out, rng, cfg)
    if rng.random() < cfg.p_rotate:
        out = rotate_xy(out, float(rng.uniform(-cfg.max_rotation_deg, cfg.max_rotation_deg)))
    if rng.random() < cfg.p_scale:
        out = out * np.float32(rng.uniform(*cfg.scale_range))
    return out.astype(np.float32)


@dataclass(frozen=True)
class DeployAugmentConfig:
    """Augmentation for the deployment gap (docs/evaluation/BROWSER_PATH.md): what a browser webcam path changes relative to INCLUDE.

    All three act on normalized features. The y scale is exact (it is re-normalized by the new shoulder width, see y_scale_features); the
    noise is given in image fractions and converted with the median INCLUDE shoulder width; dropout removes a whole hand for a frame.
    """

    y_scale_range: tuple[float, float] = (0.85, 1.20)
    p_y_scale: float = 0.8
    noise_img_max: float = 0.01  # per sample sigma drawn from U(0, this), in fractions of the image size
    ref_shoulder_width: float = 0.133  # median shoulder width of the INCLUDE videos as a fraction of the picture width
    hand_drop_max: float = 0.2  # per sample probability drawn from U(0, this), applied per frame and per hand


def y_scale_features(x: np.ndarray, s: float) -> np.ndarray:
    """Features as if the landmark y of the image had been multiplied by s before normalization (a wrong or different picture aspect).

    Normalized coordinates are (p - origin) / w with w the 2D shoulder distance. After the scaling only y changes, and w becomes
    hypot(dx, s * dy) of the shoulder vector, so every coordinate is (x, s * y, z) divided by that factor. Zero rows (no pose) and zero hand
    blocks stay zero.
    """
    out = x.astype(np.float32, copy=True).reshape(x.shape[0], -1, 3)
    shoulder = out[:, 11, :2] - out[:, 12, :2]
    w = np.hypot(shoulder[:, 0], s * shoulder[:, 1])
    out[..., 1] *= np.float32(s)
    ok = w > 1e-6
    out[ok] /= w[ok].astype(np.float32)[:, None, None]
    return out.reshape(x.shape)


def landmark_noise(x: np.ndarray, rng: np.random.Generator, sigma_feat: float) -> np.ndarray:
    """Independent Gaussian jitter on x and y of every detected landmark in every frame (missing points stay exactly zero)."""
    out = x.astype(np.float32, copy=True).reshape(x.shape[0], -1, 3)
    present = out.any(axis=2)
    out[..., :2] += (rng.normal(0.0, sigma_feat, size=out[..., :2].shape) * present[..., None]).astype(np.float32)
    return out.reshape(x.shape)


def drop_hands(x: np.ndarray, rng: np.random.Generator, p: float) -> np.ndarray:
    """Zero the whole left or right hand block of a frame with probability p, independently per frame and hand."""
    from app.recognition.preprocess import LEFT_END, POSE_END

    out = x.astype(np.float32, copy=True)
    for block in (slice(POSE_END, LEFT_END), slice(LEFT_END, FEATURE_DIM)):
        out[rng.random(out.shape[0]) < p, block] = 0.0
    return out


def deploy_augment(x: np.ndarray, rng: np.random.Generator, cfg: DeployAugmentConfig | None = None) -> np.ndarray:
    cfg = cfg or DeployAugmentConfig()
    if x.ndim != 2 or x.shape[1] != FEATURE_DIM:
        raise ValueError(f"expected shape (T, {FEATURE_DIM}), got {x.shape}")
    out = x.astype(np.float32, copy=True)
    if rng.random() < cfg.p_y_scale:
        out = y_scale_features(out, float(rng.uniform(*cfg.y_scale_range)))
    sigma = float(rng.uniform(0.0, cfg.noise_img_max)) / cfg.ref_shoulder_width
    if sigma > 0:
        out = landmark_noise(out, rng, sigma)
    return drop_hands(out, rng, float(rng.uniform(0.0, cfg.hand_drop_max)))
