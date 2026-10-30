"""Self-recorded sign takes: quality check, storage (landmarks only, never video) and retargeting to an unreviewed clip.

Features use the same 225 value per frame format as INCLUDE (see app.recognition.landmarks). A take is rejected, and not stored, when
it is too short, the body is lost in too many frames, or no hand is visible in too many frames.
"""

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from app.recognition.landmarks import FEATURE_DIM, normalize_frame
from app.recognition.preprocess import hand_missing_mask
from app.schemas.landmarks import LandmarkFrame
from retarget.clip_builder import build_clip

MIN_FRAMES = 20
MIN_FPS = 5.0
MAX_FPS = 60.0
MAX_NO_POSE_FRACTION = 0.10
MAX_NO_HAND_FRACTION = 0.30  # frames in which neither hand was detected
GLOSS_RE = re.compile(r"^[A-Z0-9][A-Z0-9-]{0,31}$")

LICENSE_NOTE = "Self-recorded by the SignBridge user; not redistributed. Not signer reviewed."


class RecordingError(ValueError):
    pass


@dataclass
class TakeStats:
    frames: int = 0
    no_pose_frames: int = 0
    no_hand_frames: int = 0
    left_missing_frames: int = 0
    right_missing_frames: int = 0
    fps: float = 0.0
    seconds: float = 0.0


@dataclass
class QualityResult:
    accepted: bool
    reasons: list[str] = field(default_factory=list)
    stats: TakeStats = field(default_factory=TakeStats)


def clean_gloss(raw: str) -> str:
    g = raw.strip().upper().replace("_", "-").replace(" ", "-")
    if not GLOSS_RE.match(g):
        raise RecordingError("Gloss must be 1 to 32 characters: letters, digits and hyphens, starting with a letter or digit.")
    return g


def frames_to_features(frames: list[LandmarkFrame]) -> tuple[np.ndarray, np.ndarray]:
    """(T, 225) features and a (T,) bool array that is True where the body pose was usable."""
    rows, valid = [], []
    for f in frames:
        feats, rep = normalize_frame(f)
        rows.append(feats)
        valid.append(rep.valid)
    return np.stack(rows).astype(np.float32), np.array(valid, dtype=bool)


def check_take(features: np.ndarray, pose_ok: np.ndarray, fps: float) -> QualityResult:
    n = int(features.shape[0])
    left, right = hand_missing_mask(features)
    no_hand = left & right & pose_ok
    stats = TakeStats(
        frames=n, no_pose_frames=int((~pose_ok).sum()), no_hand_frames=int(no_hand.sum()),
        left_missing_frames=int((left & pose_ok).sum()), right_missing_frames=int((right & pose_ok).sum()),
        fps=round(fps, 2), seconds=round(n / fps, 2) if fps > 0 else 0.0,
    )
    reasons: list[str] = []
    if not (MIN_FPS <= fps <= MAX_FPS):
        reasons.append(f"The measured frame rate {fps:.1f} fps is outside {MIN_FPS:g} to {MAX_FPS:g}; the timing of the clip would be wrong.")
    if n < MIN_FRAMES:
        reasons.append(f"Only {n} frames were captured; at least {MIN_FRAMES} are needed.")
    else:
        if stats.no_pose_frames / n > MAX_NO_POSE_FRACTION:
            reasons.append(
                f"The body was not detected in {stats.no_pose_frames} of {n} frames ({stats.no_pose_frames / n:.0%}); at most "
                f"{MAX_NO_POSE_FRACTION:.0%} are allowed. Stand back so head and shoulders are in view."
            )
        if stats.no_hand_frames / n > MAX_NO_HAND_FRACTION:
            reasons.append(
                f"No hand was detected in {stats.no_hand_frames} of {n} frames ({stats.no_hand_frames / n:.0%}); at most "
                f"{MAX_NO_HAND_FRACTION:.0%} are allowed. Keep your hands in view and well lit."
            )
    return QualityResult(accepted=not reasons, reasons=reasons, stats=stats)


def save_take(record_dir: Path, gloss: str, features: np.ndarray, stats: TakeStats, now: datetime | None = None) -> tuple[Path, str]:
    """Write <record_dir>/<gloss>/<stamp>.npy (features) and .json (metadata). Never overwrites an existing take."""
    if features.ndim != 2 or features.shape[1] != FEATURE_DIM:
        raise RecordingError("features must be (T, 225)")
    now = now or datetime.now(timezone.utc)
    stamp = now.strftime("%Y%m%dT%H%M%S%fZ")
    d = record_dir / gloss
    d.mkdir(parents=True, exist_ok=True)
    npy = d / f"{stamp}.npy"
    if npy.exists():
        raise RecordingError("a take with this timestamp already exists")
    np.save(npy, features)
    meta = {"gloss": gloss, "recorded_at_utc": now.isoformat(), "stats": stats.__dict__, "feature_dim": FEATURE_DIM,
            "contains_video": False, "origin": "self-recorded"}
    (d / f"{stamp}.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")
    return npy, stamp


def take_to_clip(features: np.ndarray, gloss: str, stats: TakeStats, feature_file: str) -> dict:
    """Retarget a take. The measured fps is used with stride 1; the clip is marked self-recorded and not signer reviewed."""
    sample = {"kind": "self-recorded", "feature_file": feature_file, **stats.__dict__}
    clip = build_clip(
        features, gloss, fps=stats.fps, stride=1, author="SignBridge user (self-recorded)", license_text=LICENSE_NOTE,
        description=f"UNREVIEWED automatic retarget of a self-recorded take ({stats.frames} frames at {stats.fps} fps); not a verified sign",
        sample=sample,
    )
    clip["source"]["origin"] = "self-recorded"
    return clip
