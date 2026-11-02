"""Compare browser MediaPipe landmarks with Python MediaPipe landmarks on the SAME recording. Run from backend/:

    python -m training.compare_landmarks --video <take>.webm --landmarks <take>.landmarks.json [--model-dir models] [--out report.json]

The two input files come from the "Landmark check" tab of the web app (both are saved to the browser's download folder; nothing is uploaded).
The video is run through Python MediaPipe Holistic with the same options as the dataset extraction (`training.video_features`), both
landmark sets go through the same `normalize_frame`, frames are paired by time, and the report gives, in shoulder widths (the unit of the
225 features): the distance between the two landmark sets (pose, arms, hands), how often each side detected the pose and each hand, and what
the trained model predicts from each set. Read only; it never changes the model or the data.
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np

from app.recognition.landmarks import FEATURE_DIM, HAND_POINTS, POSE_POINTS, normalize_frame
from app.recognition.preprocess import hand_missing_mask
from app.schemas.landmarks import LandmarkFrame

POSE_END = POSE_POINTS * 3
LEFT_END = POSE_END + HAND_POINTS * 3
ARM_POINTS = [11, 12, 13, 14, 15, 16]  # shoulders, elbows, wrists (MediaPipe pose indices)


class CompareError(ValueError):
    pass


def load_browser(path: Path) -> tuple[list[LandmarkFrame], np.ndarray, dict]:
    """Browser landmark file: {version, video_duration_ms, frames: [{t, pose, left_hand, right_hand}]} with t in ms from the start of the video."""
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        frames = [LandmarkFrame(pose=f.get("pose"), left_hand=f.get("left_hand"), right_hand=f.get("right_hand")) for f in raw["frames"]]
        times = np.array([float(f["t"]) for f in raw["frames"]])
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise CompareError(f"cannot read browser landmarks {path}: {exc}") from None
    if len(frames) < 2:
        raise CompareError("the browser file has fewer than 2 frames")
    return frames, times, {k: v for k, v in raw.items() if k != "frames"}


def python_landmarks(video: Path, duration_ms: float | None = None) -> tuple[list[LandmarkFrame], np.ndarray]:
    """Run Python MediaPipe Holistic on every frame (same options as training). Returns frames (None parts when not detected) and times in ms."""
    import cv2
    import mediapipe as mp

    from training.video_features import results_to_frame

    cap = cv2.VideoCapture(str(video))
    if not cap.isOpened():
        raise CompareError(f"cannot open video {video}")
    frames, stamps = [], []
    try:
        with mp.solutions.holistic.Holistic(static_image_mode=False, model_complexity=0) as holistic:
            while True:
                ok, bgr = cap.read()
                if not ok:
                    break
                stamps.append(cap.get(cv2.CAP_PROP_POS_MSEC))
                frames.append(results_to_frame(holistic.process(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB))))
        fps = cap.get(cv2.CAP_PROP_FPS)
    finally:
        cap.release()
    if len(frames) < 2:
        raise CompareError("the video has fewer than 2 readable frames")
    times = np.array(stamps, dtype=float)
    if not (np.all(np.diff(times) > 0) and times[-1] > 0):  # MediaRecorder files often carry no usable timestamps
        if duration_ms:
            times = np.linspace(0, duration_ms, len(frames), endpoint=False)
        elif fps and fps > 0:
            times = np.arange(len(frames)) * 1000.0 / fps
        else:
            raise CompareError("the video has no usable timestamps; the browser file must give video_duration_ms")
    return frames, times


def to_features(frames: list[LandmarkFrame]) -> tuple[np.ndarray, np.ndarray]:
    """(T, 225) features and a (T,) mask of frames with a usable pose (the same normalization as training and the API)."""
    rows, ok = [], []
    for f in frames:
        feats, rep = normalize_frame(f)
        rows.append(feats)
        ok.append(rep.valid)
    return np.stack(rows).astype(np.float32), np.array(ok, dtype=bool)


def pair_by_time(t_a: np.ndarray, t_b: np.ndarray, tol_ms: float) -> list[tuple[int, int]]:
    """For every frame of A, the nearest frame of B within tol_ms (each B frame used at most once, in time order)."""
    pairs, used = [], set()
    for i, t in enumerate(t_a):
        j = int(np.argmin(np.abs(t_b - t)))
        if abs(t_b[j] - t) <= tol_ms and j not in used:
            pairs.append((i, j))
            used.add(j)
    return pairs


def _stats(values: list[float]) -> dict | None:
    if not values:
        return None
    a = np.array(values)
    return {"frames": len(a), "median": float(np.median(a)), "mean": float(a.mean()), "p95": float(np.percentile(a, 95))}


def landmark_distance(fa: np.ndarray, fb: np.ndarray, start: int, count: int, points: list[int] | None = None) -> float:
    """Mean Euclidean distance (shoulder widths) between corresponding landmarks of one group in one frame."""
    a = fa[start : start + count * 3].reshape(count, 3)
    b = fb[start : start + count * 3].reshape(count, 3)
    idx = points if points is not None else list(range(count))
    return float(np.linalg.norm(a[idx] - b[idx], axis=1).mean())


def compare_features(
    fb: np.ndarray, ok_b: np.ndarray, fp: np.ndarray, ok_p: np.ndarray, pairs: list[tuple[int, int]]
) -> dict:
    """Distances and detection agreement over the paired frames. B = browser, P = Python."""
    pose, arms, left, right = [], [], [], []
    det = {"pose": {"both": 0, "browser_only": 0, "python_only": 0, "neither": 0}}
    for side in ("left_hand", "right_hand"):
        det[side] = {"both": 0, "browser_only": 0, "python_only": 0, "neither": 0}
    lb, rb = hand_missing_mask(fb)
    lp, rp = hand_missing_mask(fp)
    for ib, ip in pairs:
        pb, pp = bool(ok_b[ib]), bool(ok_p[ip])
        det["pose"]["both" if pb and pp else "browser_only" if pb else "python_only" if pp else "neither"] += 1
        if pb and pp:
            pose.append(landmark_distance(fb[ib], fp[ip], 0, POSE_POINTS))
            arms.append(landmark_distance(fb[ib], fp[ip], 0, POSE_POINTS, ARM_POINTS))
        for side, mb, mp_, start, out in (("left_hand", lb, lp, POSE_END, left), ("right_hand", rb, rp, LEFT_END, right)):
            hb, hp = pb and not mb[ib], pp and not mp_[ip]
            det[side]["both" if hb and hp else "browser_only" if hb else "python_only" if hp else "neither"] += 1
            if hb and hp:
                out.append(landmark_distance(fb[ib], fp[ip], start, HAND_POINTS))
    return {
        "paired_frames": len(pairs),
        "distance_in_shoulder_widths": {"pose_33_points": _stats(pose), "arms_shoulder_to_wrist": _stats(arms), "left_hand": _stats(left), "right_hand": _stats(right)},
        "detection_agreement": det,
    }


def model_view(features: np.ndarray, ok: np.ndarray, model_dir: Path) -> dict:
    """What the trained model predicts from one landmark set (valid frames only, as the live path does)."""
    from app.recognition.artifacts import ModelLoadError
    from app.recognition.inference import get_recognizer

    rows = features[ok]
    if len(rows) < 8:
        return {"error": f"only {len(rows)} usable frame(s)"}
    try:
        preds = get_recognizer(model_dir).predict(rows, top_k=3)
    except ModelLoadError as exc:
        return {"error": str(exc)}
    return {"frames_used": int(len(rows)), "top3": [{"label": p.label, "confidence": round(p.confidence, 4)} for p in preds]}


def verdict(report: dict) -> str:
    d = report["distance_in_shoulder_widths"]
    arms = d["arms_shoulder_to_wrist"]
    parts = []
    if not arms:
        return "No frame had a usable pose in both sets, so landmark distances could not be compared."
    parts.append(f"arm landmarks differ by a median of {arms['median']:.3f} shoulder widths")
    for name in ("left_hand", "right_hand"):
        if d[name]:
            parts.append(f"{name.replace('_', ' ')} median {d[name]['median']:.3f}")
    return "; ".join(parts) + ". For scale: a hand is about 0.4 to 0.5 shoulder widths across, so values near 0.05 or below are small and values above 0.15 are large."


def run(video: Path, landmarks: Path, model_dir: Path | None) -> dict:
    frames_b, t_b, meta = load_browser(landmarks)
    frames_p, t_p = python_landmarks(video, meta.get("video_duration_ms"))
    fb, ok_b = to_features(frames_b)
    fp, ok_p = to_features(frames_p)
    tol = max(float(np.median(np.diff(t_b))), float(np.median(np.diff(t_p)))) * 0.75
    pairs = pair_by_time(t_b, t_p, tol)
    if len(pairs) < 5:
        raise CompareError(f"only {len(pairs)} frame pairs could be matched by time (browser {len(t_b)} frames, Python {len(t_p)} frames)")
    report = compare_features(fb, ok_b, fp, ok_p, pairs)
    report["frames"] = {"browser": len(t_b), "python": len(t_p), "browser_with_pose": int(ok_b.sum()), "python_with_pose": int(ok_p.sum())}
    report["browser_extraction_fps"] = round(1000.0 * (len(t_b) - 1) / max(t_b[-1] - t_b[0], 1.0), 2)
    report["summary"] = verdict(report)
    if model_dir is not None:
        report["model"] = {"browser_landmarks": model_view(fb, ok_b, model_dir), "python_landmarks": model_view(fp, ok_p, model_dir)}
    return report


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--video", type=Path, required=True)
    p.add_argument("--landmarks", type=Path, required=True)
    p.add_argument("--model-dir", type=Path, default=Path("models"))
    p.add_argument("--out", type=Path)
    a = p.parse_args()
    try:
        report = run(a.video, a.landmarks, a.model_dir if a.model_dir.is_dir() else None)
    except CompareError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    out = a.out or a.landmarks.with_suffix(".comparison.json")
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    print(f"\nwritten to {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
