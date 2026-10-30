import csv

import numpy as np

from app.recognition.landmarks import FEATURE_DIM
from training.audit_include import audit


def test_audit_reports_missing_listed_videos_and_hand_rates(tmp_path) -> None:
    raw, out = tmp_path / "raw", tmp_path / "out"
    (raw / "splits").mkdir(parents=True)
    (out / "_parts").mkdir(parents=True)
    (raw / "splits" / "include_train.txt").write_text("A/1. X/a.MOV\nA/1. X/b.MOV\n")
    (raw / "splits" / "include_val.txt").write_text("A/2. Y/c.MOV\n")
    (raw / "splits" / "include_test.txt").write_text("A/2. Y/d.MOV\n")

    arr = np.ones((10, FEATURE_DIM), dtype=np.float32)
    arr[:4, 99:162] = 0  # left hand missing in 4 of 10 frames
    np.save(out / "1.npy", arr)
    np.save(out / "2.npy", np.ones((6, FEATURE_DIM), dtype=np.float32))
    fields = ["member", "npy", "message", "split", "label", "category"]
    rows = [
        dict(member="A/1. X/a.MOV", npy="1.npy", message="", split="train", label="X", category="A"),
        dict(member="A/2. Y/c.MOV", npy="2.npy", message="", split="val", label="Y", category="A"),
        dict(member="A/2. Y/d.MP4", npy="", message="", split="test", label="Y", category="A"),  # extension differs: not a match
    ]
    with (out / "_parts" / "z.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows[:2])
    with (out / "manifest.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["path", "label", "signer_id", "split"])
        w.writerow(["1.npy", "X", "unknown", "train"])
        w.writerow(["2.npy", "Y", "unknown", "val"])

    quality, split, classes = audit(raw, out)
    assert quality["integrity"]["problem_counts"] == {} and quality["statistics"]["total_usable_samples"] == 2
    assert split["per_split"]["train"]["never_seen_in_any_zip"] == 1  # b.MOV
    assert split["per_split"]["test"]["never_seen_in_any_zip"] == 1  # d.MOV
    assert split["signer_ids_available"] is False and "UNVERIFIED" in split["labelling"]
    x = next(c for c in classes if c["label"] == "X")
    assert x["frame_no_left_hand_rate"] == 0.4 and x["frame_no_right_hand_rate"] == 0.0


def test_audit_flags_corrupt_and_wrong_shape_files(tmp_path) -> None:
    raw, out = tmp_path / "raw", tmp_path / "out"
    (raw / "splits").mkdir(parents=True)
    (out / "_parts").mkdir(parents=True)
    for n in ("include_train.txt", "include_val.txt", "include_test.txt"):
        (raw / "splits" / n).write_text("")
    (out / "bad.npy").write_bytes(b"not numpy")
    np.save(out / "shape.npy", np.ones((5, 10), dtype=np.float32))
    np.save(out / "nan.npy", np.full((5, FEATURE_DIM), np.nan, dtype=np.float32))
    with (out / "manifest.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["path", "label", "signer_id", "split"])
        for p in ("bad.npy", "shape.npy", "nan.npy", "gone.npy"):
            w.writerow([p, "X", "unknown", "train"])
    quality, _, _ = audit(raw, out)
    assert quality["integrity"]["problem_counts"] == {"unreadable": 1, "bad_shape": 1, "non_finite": 1, "missing_file": 1}
