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
from app.recognition.segmenter import SignSegmenter
from app.schemas.landmarks import LandmarkFrame
from retarget.clip_builder import build_clip

MIN_FRAMES = 20
MIN_FPS = 5.0
MAX_FPS = 60.0
MAX_NO_POSE_FRACTION = 0.10
MAX_NO_HAND_FRACTION = 0.30  # frames in which neither hand was detected
GLOSS_RE = re.compile(r"^[A-Z0-9][A-Z0-9-]{0,31}$")
SIGNER_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,31}$")
# Grammar words recorded first (the sentences used in the examples need them); the rest of the 50 follow in alphabetical order.
PRIORITY_GLOSSES = ["WHERE", "GO", "LIKE", "NOT", "HELP", "WHAT", "YES", "NO"]

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
    segments: int = 0  # signs the segmenter finds in the take (a good take has exactly one)


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


def clean_signer(raw: str) -> str:
    """Signer ID for the folder name: letters, digits, hyphen and underscore, upper cased (for example P01). Never a path."""
    sid = raw.strip()
    if not SIGNER_RE.match(sid):
        raise RecordingError("Signer ID must be 1 to 32 characters: letters, digits, hyphen or underscore, starting with a letter or digit.")
    return sid.upper()


def grammar_words(lex) -> list[str]:
    """The glosses to record for the guided session: dictionary entries that are not INCLUDE classes, priority words first."""
    words = sorted(g for g, s in lex.signs.items() if s.source != "include")
    first = [g for g in PRIORITY_GLOSSES if g in words]
    return first + [g for g in words if g not in first]


def alphabet_glosses() -> list[str]:
    """FS-A to FS-Z: the clip names the avatar looks for when it spells a word (frontend letterGloss)."""
    return [f"FS-{c}" for c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ"]


def find_segments(features: np.ndarray, pose_ok: np.ndarray) -> list:
    """The signs the live segmenter would find in this take (frames without a body pose are skipped, as live)."""
    seg = SignSegmenter()
    found = []
    for row in features[pose_ok]:
        found += seg.push(row)
    found += seg.flush()
    return found


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
    if n >= MIN_FRAMES and not reasons:
        stats.segments = len(find_segments(features, pose_ok))
        if stats.segments == 0:
            reasons.append("No sign movement was detected: raise your hands to sign right after the countdown, then lower them (or hold still) when you finish.")
    return QualityResult(accepted=not reasons, reasons=reasons, stats=stats)


def take_dir(record_dir: Path, gloss: str, signer_id: str | None = None) -> Path:
    """data/recorded/<SIGNER>/<GLOSS> for a guided session, data/recorded/<GLOSS> for a single recording without a signer ID."""
    return record_dir / signer_id / gloss if signer_id else record_dir / gloss


def count_takes(record_dir: Path, signer_id: str) -> dict[str, int]:
    """Saved takes per gloss for one signer (so a session can resume where it stopped)."""
    base = record_dir / signer_id
    if not base.is_dir():
        return {}
    return {d.name: n for d in sorted(base.iterdir()) if d.is_dir() and (n := len(list(d.glob("*.npy"))))}


def save_take(
    record_dir: Path, gloss: str, features: np.ndarray, stats: TakeStats, now: datetime | None = None, signer_id: str | None = None
) -> tuple[Path, str]:
    """Write <take dir>/<stamp>.npy (features) and .json (metadata). Never overwrites an existing take."""
    if features.ndim != 2 or features.shape[1] != FEATURE_DIM:
        raise RecordingError("features must be (T, 225)")
    now = now or datetime.now(timezone.utc)
    stamp = now.strftime("%Y%m%dT%H%M%S%fZ")
    d = take_dir(record_dir, gloss, signer_id)
    d.mkdir(parents=True, exist_ok=True)
    npy = d / f"{stamp}.npy"
    if npy.exists():
        raise RecordingError("a take with this timestamp already exists")
    np.save(npy, features)
    meta = {"gloss": gloss, "recorded_at_utc": now.isoformat(), "stats": stats.__dict__, "feature_dim": FEATURE_DIM,
            "contains_video": False, "origin": "self-recorded", "signer_id": signer_id}
    (d / f"{stamp}.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")
    return npy, stamp


def take_to_clip(features: np.ndarray, gloss: str, stats: TakeStats, feature_file: str, signer_id: str | None = None) -> dict:
    """Retarget a take. The measured fps is used with stride 1; the clip is marked self-recorded and not signer reviewed."""
    sample = {"kind": "self-recorded", "feature_file": feature_file, "signer_id": signer_id, **stats.__dict__}
    clip = build_clip(
        features, gloss, fps=stats.fps, stride=1, author="SignBridge user (self-recorded)", license_text=LICENSE_NOTE,
        description=f"UNREVIEWED automatic retarget of a self-recorded take ({stats.frames} frames at {stats.fps} fps); not a verified sign",
        sample=sample,
    )
    clip["source"]["origin"] = "self-recorded"
    return clip
