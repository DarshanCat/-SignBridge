"""Attach the SOURCE landmarks of each clip to the clip file, so the avatar can retarget from them at run time.

A clip stores only the rotations that make.py derived from one INCLUDE sample (16 tracks). That is not enough to recover finger spread, thumb
opposition or where a hand is relative to the face, and it cannot be fitted to an avatar with other proportions. This script adds a top level key
"landmarks" with the normalized landmarks of the same sample (the file named in source.source_sample.feature_file), at the times of the
clip's keyframes. The rotation tracks are NOT touched, the backend validator ignores the extra key, and the recognition model and the
evaluation results are not involved.

    python -m retarget.add_source_landmarks --clips ..\\frontend\\public\\animations --features ..\\data\\processed\\include ..\\data\\processed\\include_v2

Landmark layout (rig axes are NOT applied here; the values are the stored normalized features: origin shoulder midpoint, unit shoulder width,
image axes x right, y down, z depth). Rounded to 3 decimals.
"""

import argparse
import json
from pathlib import Path

import numpy as np

from app.recognition.landmarks import HAND_POINTS, POSE_POINTS

POSE_KEEP = [0, 2, 5, 9, 10, 11, 12, 13, 14, 15, 16]  # nose, eyes, mouth corners, shoulders, elbows, wrists
POSE_END = POSE_POINTS * 3
LEFT_END = POSE_END + HAND_POINTS * 3
VERSION = 1


def landmarks_block(seq: np.ndarray, times: list[float]) -> dict:
    pose = [[[round(float(v), 3) for v in f[i * 3 : i * 3 + 3]] for i in POSE_KEEP] for f in seq]

    def hand(start: int):
        out = []
        for f in seq:
            block = f[start : start + HAND_POINTS * 3]
            out.append(None if not block.any() else [[round(float(v), 3) for v in block[i * 3 : i * 3 + 3]] for i in range(HAND_POINTS)])
        return out

    return {"version": VERSION, "t": times, "pose_idx": POSE_KEEP, "pose": pose, "left": hand(POSE_END), "right": hand(LEFT_END)}


def keyframe_times(clip: dict, frames: int) -> list[float]:
    keys = max((t["keyframes"] for t in clip["tracks"]), key=len)
    times = [k["t"] for k in keys[1:-1]]  # the first and last keyframes are the rest ramps
    if len(times) != frames:
        raise ValueError(f"{len(times)} keyframes inside the ramps but {frames} source frames")
    return times


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--clips", type=Path, required=True)
    p.add_argument("--features", type=Path, nargs="+", required=True)
    p.add_argument("--dry-run", action="store_true")
    a = p.parse_args()
    done = skipped = 0
    for path in sorted(a.clips.glob("*.json")):
        if path.name == "index.json":
            continue
        clip = json.loads(path.read_text(encoding="utf-8"))
        sample = (clip.get("source") or {}).get("source_sample") or {}
        name = sample.get("feature_file")
        feat = next((d / name for d in a.features if name and (d / name).is_file()), None)
        if feat is None:
            print(f"skip {path.name}: no source feature file")
            skipped += 1
            continue
        seq = np.load(feat)
        if seq.ndim != 2 or seq.shape[1] != 225:
            print(f"skip {path.name}: bad feature shape {seq.shape}")
            skipped += 1
            continue
        clip["landmarks"] = landmarks_block(seq, keyframe_times(clip, seq.shape[0]))
        if not a.dry_run:
            path.write_text(json.dumps(clip, separators=(",", ":")), encoding="utf-8")
        done += 1
    print(f"landmarks added to {done} clips, skipped {skipped}")


if __name__ == "__main__":
    main()
