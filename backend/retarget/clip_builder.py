"""Turn a normalized landmark sequence (T, 225) into a SignBridge animation clip (JSON, validated by app.avatar.clip.ClipFile)."""

import numpy as np

from app.avatar.clip import BONES, MAX_DURATION, ClipFile
from retarget.pose_to_rig import frame_to_bones

HAND_BONE_PREFIX = {"l": "hand_l", "r": "hand_r"}
HOLD_FRAMES = 4  # keep the last hand pose this long when the hand drops out, then relax to rest
RELAX_FRAMES = 4


def sequence_to_tracks(seq: np.ndarray) -> dict[str, np.ndarray]:
    """Per bone array (T, 3) of Euler XYZ angles. Frames with unusable arm landmarks repeat the previous valid frame."""
    if seq.ndim != 2 or seq.shape[1] != 225 or seq.shape[0] < 2:
        raise ValueError("need a (T, 225) sequence with at least 2 frames")
    t_len = seq.shape[0]
    out = {b: np.zeros((t_len, 3)) for b in BONES}
    last: dict[str, tuple[float, float, float]] | None = None
    missing_run = {"l": 0, "r": 0}
    for t in range(t_len):
        try:
            bones, present = frame_to_bones(seq[t])
            last = bones
        except ValueError:
            if last is None:
                continue
            bones, present = last, {"l": True, "r": True}
        for side in ("l", "r"):
            prefix = HAND_BONE_PREFIX[side]
            hand_bones = [b for b in BONES if b == prefix or b.startswith(prefix + ".")]
            if present[side]:
                missing_run[side] = 0
                for b in hand_bones:
                    out[b][t] = bones[b]
            else:  # hold briefly, then relax toward the rest pose instead of inventing a hand
                missing_run[side] += 1
                k = missing_run[side]
                for b in hand_bones:
                    prev = out[b][t - 1] if t > 0 else np.zeros(3)
                    out[b][t] = prev if k <= HOLD_FRAMES else prev * max(0.0, 1.0 - 1.0 / RELAX_FRAMES)
        for b in BONES:
            if b.startswith(("upperArm", "foreArm")):
                out[b][t] = bones[b]
    for b in BONES:  # unwrap so interpolation never spins the long way round
        out[b] = np.unwrap(out[b], axis=0)
    return out


def smooth(a: np.ndarray, window: int = 3) -> np.ndarray:
    if window <= 1 or len(a) < window:
        return a
    pad = window // 2
    p = np.pad(a, ((pad, pad), (0, 0)), mode="edge")
    return np.stack([np.convolve(p[:, i], np.ones(window) / window, mode="valid") for i in range(a.shape[1])], axis=1)


def build_clip(
    seq: np.ndarray, gloss: str, *, fps: float = 30.0, stride: int = 2, ramp_s: float = 0.25, author: str,
    license_text: str, description: str, sample: dict | None = None,
) -> dict:
    """fps is the SOURCE video frame rate (assumed, not verified) and stride the frame step used when the features were extracted."""
    tracks_arr = {b: smooth(a) for b, a in sequence_to_tracks(seq).items()}
    dt = stride / fps
    n = seq.shape[0]
    duration = (n - 1) * dt + 2 * ramp_s
    if duration > MAX_DURATION:
        raise ValueError(f"clip would last {duration:.1f}s, over the {MAX_DURATION}s limit")
    tracks = []
    for b, a in tracks_arr.items():
        if float(np.abs(a).max()) < 1e-3:
            continue
        keys = [{"t": 0.0, "rot": [0.0, 0.0, 0.0]}]
        keys += [{"t": round(ramp_s + i * dt, 4), "rot": [round(float(v), 4) for v in a[i]]} for i in range(n)]
        keys.append({"t": round(duration, 4), "rot": [0.0, 0.0, 0.0]})
        tracks.append({"bone": b, "keyframes": keys})
    clip = {
        "gloss": gloss.upper(), "duration": round(duration, 4), "tracks": tracks,
        "source": {"author": author, "license": license_text, "description": description, "review_status": "not_signer_reviewed", "source_sample": sample},
    }
    ClipFile.model_validate(clip)  # raises if the clip would be rejected by the registry
    return clip
