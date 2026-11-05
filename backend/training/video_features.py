"""Extract normalized landmark features from video files with Python MediaPipe Holistic.

The conversion reuses app.recognition.landmarks.normalize_frame, so training features are
identical to what the API computes for browser-extracted landmarks. Left/right hands are taken
as MediaPipe reports them (the same convention as the browser).
"""

import csv
from pathlib import Path
from typing import Any

import numpy as np

from app.recognition.landmarks import normalize_frame
from app.schemas.landmarks import LandmarkFrame, Point
from training.data import DatasetError

MAX_FRAMES = 300
MIN_USABLE_FRAMES = 8


def _points(lms: Any) -> list[Point] | None:
    if lms is None:
        return None
    return [Point(x=p.x, y=p.y, z=p.z) for p in lms.landmark]


def results_to_frame(results: Any) -> LandmarkFrame:
    return LandmarkFrame(
        pose=_points(results.pose_landmarks),
        left_hand=_points(results.left_hand_landmarks),
        right_hand=_points(results.right_hand_landmarks),
    )


def video_to_features(video: Path, stride: int = 1) -> np.ndarray:
    """Return a (T, 225) array of valid frames. Raises DatasetError if the video is unusable."""
    import cv2
    import mediapipe as mp

    cap = cv2.VideoCapture(str(video))
    if not cap.isOpened():
        raise DatasetError(f"Cannot open video: {video}")
    rows: list[np.ndarray] = []
    try:
        with mp.solutions.holistic.Holistic(static_image_mode=False, model_complexity=0) as holistic:
            index = 0
            while len(rows) < MAX_FRAMES:
                ok, bgr = cap.read()
                if not ok:
                    break
                index += 1
                if (index - 1) % stride:
                    continue
                results = holistic.process(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB))
                feats, report = normalize_frame(results_to_frame(results))
                if report.valid:
                    rows.append(feats)
    finally:
        cap.release()
    if len(rows) < MIN_USABLE_FRAMES:
        raise DatasetError(f"{video.name}: only {len(rows)} usable frame(s) (pose not detected)")
    return np.stack(rows)


def video_to_features_face(video: Path, stride: int = 1) -> tuple[np.ndarray, np.ndarray]:
    """Like video_to_features, and also the face block (T, FACE_DIM) of the same frames. The body block is identical to video_to_features' output."""
    import cv2
    import mediapipe as mp

    from app.recognition.face import face_block, select_face

    cap = cv2.VideoCapture(str(video))
    if not cap.isOpened():
        raise DatasetError(f"Cannot open video: {video}")
    rows: list[np.ndarray] = []
    faces: list[np.ndarray] = []
    try:
        with mp.solutions.holistic.Holistic(static_image_mode=False, model_complexity=0) as holistic:
            index = 0
            while len(rows) < MAX_FRAMES:
                ok, bgr = cap.read()
                if not ok:
                    break
                index += 1
                if (index - 1) % stride:
                    continue
                results = holistic.process(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB))
                frame = results_to_frame(results)
                feats, report = normalize_frame(frame)
                if report.valid:
                    rows.append(feats)
                    faces.append(face_block(frame.model_copy(update={"face": select_face(_points(results.face_landmarks))})))
    finally:
        cap.release()
    if len(rows) < MIN_USABLE_FRAMES:
        raise DatasetError(f"{video.name}: only {len(rows)} usable frame(s) (pose not detected)")
    return np.stack(rows), np.stack(faces)


def process_videos(index_csv: Path, out_dir: Path, stride: int = 1) -> tuple[int, list[str]]:
    """index_csv columns: video,label,signer_id (video path relative to the CSV).

    Writes .npy files and manifest.csv into out_dir. Returns (written, skipped messages).
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    with index_csv.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if not {"video", "label", "signer_id"} <= set(reader.fieldnames or []):
            raise DatasetError("Index CSV needs columns video,label,signer_id")
        rows = list(reader)
        has_split = "split" in (reader.fieldnames or [])

    written, skipped = [], []
    for i, r in enumerate(rows):
        name = f"{i:06d}.npy"
        try:
            np.save(out_dir / name, video_to_features(index_csv.parent / r["video"], stride))
        except DatasetError as exc:
            skipped.append(str(exc))
            continue
        written.append((name, r["label"].strip(), r["signer_id"].strip(), (r.get("split") or "").strip()))

    with (out_dir / "manifest.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["path", "label", "signer_id"] + (["split"] if has_split else []))
        w.writerows([row if has_split else row[:3] for row in written])
    with (out_dir / "exclusions.csv").open("w", newline="", encoding="utf-8") as f:  # never silently drop samples
        w = csv.writer(f)
        w.writerow(["reason"])
        w.writerows([[m] for m in skipped])
    return len(written), skipped
