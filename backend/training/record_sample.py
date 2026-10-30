"""Record consented custom ISL samples from a webcam. Run from backend/:

    python -m training.record_sample --dir ..\\data\\custom --signer-id S01 --label HELLO --consent-confirmed

Only landmark features are saved; no video or image is written. --consent-confirmed is an explicit
statement that the signer has agreed (in writing) to their landmark data being stored and used for
this project. Labels must be ISL glosses. The signer's consent is recorded in consent.csv.
"""

import argparse
import csv
import json
import sys
from datetime import date
from pathlib import Path

import numpy as np

from app.recognition.landmarks import FEATURE_DIM
from training.data import DatasetError
from training.dataset_info import INFO_FILE


def ensure_custom_dataset(directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    info = directory / INFO_FILE
    if not info.exists():
        info.write_text(
            json.dumps(
                {
                    "name": "SignBridge custom consented recordings",
                    "language": "ISL",
                    "license": "Private; use restricted to the consent scope in consent.csv",
                    "source_url": "local recording",
                    "consent_required": True,
                },
                indent=2,
            ),
            encoding="utf-8",
        )


def append_sample(directory: Path, features: np.ndarray, label: str, signer_id: str, scope: str) -> Path:
    """Save one (T, 225) feature array, add it to manifest.csv and record the signer's consent once."""
    if features.ndim != 2 or features.shape[1] != FEATURE_DIM or features.shape[0] < 1:
        raise DatasetError(f"expected shape (T, {FEATURE_DIM}), got {features.shape}")
    label, signer_id = label.strip(), signer_id.strip()
    if not label or not signer_id:
        raise DatasetError("label and signer_id must be non-empty")
    ensure_custom_dataset(directory)

    consent = directory / "consent.csv"
    known = set()
    if consent.exists():
        with consent.open(newline="", encoding="utf-8") as f:
            known = {r["signer_id"] for r in csv.DictReader(f)}
    if signer_id not in known:
        new = not consent.exists()
        with consent.open("a", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            if new:
                w.writerow(["signer_id", "consent_date", "scope"])
            w.writerow([signer_id, date.today().isoformat(), scope])

    manifest = directory / "manifest.csv"
    n = sum(1 for _ in manifest.open(encoding="utf-8")) - 1 if manifest.exists() else 0
    name = f"{signer_id}_{label}_{n:05d}.npy"
    np.save(directory / name, features.astype(np.float32))
    new = not manifest.exists()
    with manifest.open("a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["path", "label", "signer_id"])
        w.writerow([name, label, signer_id])
    return directory / name


def record_features(seconds: float) -> np.ndarray:
    import cv2
    import mediapipe as mp

    from app.recognition.landmarks import normalize_frame
    from training.video_features import results_to_frame

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        raise DatasetError("Could not open the webcam.")
    rows, end = [], cv2.getTickCount() + seconds * cv2.getTickFrequency()
    try:
        with mp.solutions.holistic.Holistic(model_complexity=0) as holistic:
            while cv2.getTickCount() < end:
                ok, bgr = cap.read()
                if not ok:
                    break
                feats, rep = normalize_frame(results_to_frame(holistic.process(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB))))
                if rep.valid:
                    rows.append(feats)
    finally:
        cap.release()
    if len(rows) < 8:
        raise DatasetError(f"Only {len(rows)} usable frame(s) captured; make sure your upper body is visible.")
    return np.stack(rows)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--dir", type=Path, required=True)
    p.add_argument("--signer-id", required=True, help="pseudonymous ID, not a real name")
    p.add_argument("--label", required=True, help="ISL gloss")
    p.add_argument("--seconds", type=float, default=3.0)
    p.add_argument("--scope", default="academic research prototype")
    p.add_argument("--consent-confirmed", action="store_true")
    a = p.parse_args()
    if not a.consent_confirmed:
        print("Refusing to record: pass --consent-confirmed after the signer has given informed consent.", file=sys.stderr)
        return 2
    try:
        path = append_sample(a.dir, record_features(a.seconds), a.label, a.signer_id, a.scope)
    except DatasetError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    print(f"Saved landmark features to {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
