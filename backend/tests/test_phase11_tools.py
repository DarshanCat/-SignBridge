"""Phase 11 tooling tests (manifest creation, splits, validation reports, class weights, evaluation).

All data here is synthetic and exists only to test code paths; none of it says anything about ISL recognition.
"""

import csv
import json
from pathlib import Path

import numpy as np
import pytest

from tests.test_training_pipeline import make_dataset
from training.data import DatasetError, read_manifest, split_samples
from training.evaluate import evaluate, to_markdown
from training.make_manifest import build_index, read_split_file, write_outputs
from training.train import train
from training.validate_dataset import validate
from training.video_features import process_videos


def test_make_manifest_labels_signers_duplicates_and_exclusions(tmp_path) -> None:
    root = tmp_path / "raw"
    for rel, data in {
        "Animals/Dog/S01_a.mp4": b"a", "Animals/Dog/S02_b.mp4": b"b", "Animals/Cat/S01_c.mp4": b"a",
        "Animals/Cat/nosigner.mp4": b"d", "top.mp4": b"e", "Animals/Cat/notes.txt": b"x",
    }.items():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_bytes(data)
    rows, excluded = build_index(root, signer_regex=r"(S\d+)", hash_duplicates=True)
    assert {(r["label"], r["signer_id"]) for r in rows} == {("Cat", "S01"), ("Dog", "S02")}  # files are visited in sorted order
    reasons = dict(excluded)
    assert "byte-identical duplicate of Animals/Cat/S01_c.mp4" in reasons["Animals/Dog/S01_a.mp4"]
    assert reasons["Animals/Cat/nosigner.mp4"] == "signer regex did not match"
    assert "no directory" in reasons["top.mp4"]
    write_outputs(rows, excluded, tmp_path / "index.csv")
    assert (tmp_path / "index.exclusions.csv").read_text().count("\n") == 4  # header + 3 reasons
    unknown_rows, _ = build_index(root)
    assert {r["signer_id"] for r in unknown_rows} == {"unknown"}


def test_make_manifest_split_file(tmp_path) -> None:
    root = tmp_path / "raw"
    for rel in ("A/x/1.mp4", "A/x/2.mp4", "A/x/3.mp4"):
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_bytes(rel.encode())
    sf = tmp_path / "s.csv"
    sf.write_text("video,split\nA/x/1.mp4,train\nA/x/2.mp4,test\n")
    rows, excluded = build_index(root, split_map=read_split_file(sf))
    assert {r["split"] for r in rows} == {"train", "test"} and excluded == [("A/x/3.mp4", "not listed in the split file")]
    sf.write_text("video,split\nA/x/1.mp4,banana\n")
    with pytest.raises(DatasetError):
        read_split_file(sf)
    with pytest.raises(DatasetError):
        build_index(tmp_path / "missing")


def add_split_column(manifest: Path, mapping) -> None:
    rows = list(csv.DictReader(manifest.open(newline="")))
    with manifest.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["path", "label", "signer_id", "split"])
        w.writeheader()
        for r in rows:
            r["split"] = mapping(r)
            w.writerow(r)


def test_predefined_split_is_used_and_validated(tmp_path) -> None:
    m = make_dataset(tmp_path, signers=4, per=2)
    add_split_column(m, lambda r: {"signer0": "test", "signer1": "val"}.get(r["signer_id"], "train"))
    splits, method = split_samples(read_manifest(m), seed=0)
    assert method == "predefined" and {s.signer for s in splits["test"]} == {"signer0"}
    add_split_column(m, lambda r: "train")
    with pytest.raises(DatasetError, match="train, val and test"):
        split_samples(read_manifest(m), seed=0)
    add_split_column(m, lambda r: "train" if r["signer_id"] == "signer0" else "")
    with pytest.raises(DatasetError, match="only some rows"):
        split_samples(read_manifest(m), seed=0)


def test_train_with_class_weights_records_choices_and_macro_metrics(tmp_path) -> None:
    m = make_dataset(tmp_path)
    report = train(m, tmp_path / "out", epochs=5, hidden=8, layers=1, class_weights=True)
    assert report["hyperparameters"]["class_weights"] is True and report["split_method"] == "signer-disjoint"
    t = report["results"]["test"]
    assert {"macro_precision", "macro_recall", "macro_f1", "num_classes_with_support"} <= t.keys()


def test_train_refuses_dataset_that_fails_validation(tmp_path) -> None:
    m = make_dataset(tmp_path)
    np.save(tmp_path / "s0_A_0.npy", np.zeros((4, 7), dtype=np.float32))
    with pytest.raises(DatasetError, match="bad shape"):
        train(m, tmp_path / "out", epochs=1)


def test_validation_reports_duplicates_and_writes_json(tmp_path) -> None:
    m = make_dataset(tmp_path, signers=4, per=5)
    np.save(tmp_path / "s0_B_0.npy", np.load(tmp_path / "s0_A_0.npy"))  # same bytes as another sample
    report = validate(tmp_path)
    assert report["duplicate_groups"] >= 1 and any("identical" in w for w in report["warnings"])
    assert report["sequence_length_frames"] == {"min": 20, "median": 20, "max": 20}
    assert sum(report["samples_per_class"].values()) == report["num_samples"] == len(read_manifest(m))


def test_evaluate_matches_training_report_and_is_deterministic(tmp_path) -> None:
    m = make_dataset(tmp_path)
    out = tmp_path / "models"
    trained = train(m, out, epochs=10, hidden=8, layers=1)
    r1, r2 = evaluate(m, out), evaluate(m, out)
    assert r1["accuracy"] == pytest.approx(trained["results"]["test"]["accuracy"])
    assert r1["confusion_matrix"] == trained["results"]["test"]["confusion_matrix"]
    assert r1["num_test_samples"] == trained["sample_counts"]["test"]
    assert r1["accuracy"] == r2["accuracy"] and r1["signer_independence_verified"] is True
    assert not set(r1["test_signers"]) & set(trained["split_signers"]["train"])
    assert "| Class |" in to_markdown(r1)
    json.dumps(r1)  # serializable


def test_evaluate_errors(tmp_path) -> None:
    m = make_dataset(tmp_path)
    with pytest.raises(DatasetError, match="metrics.json"):
        evaluate(m, tmp_path / "nomodel")
    out = tmp_path / "models"
    train(m, out, epochs=2, hidden=8, layers=1)
    (out / "isl_model.pt").write_bytes(b"junk")
    with pytest.raises(DatasetError, match="Could not load"):
        evaluate(m, out)


def test_process_videos_writes_exclusions_and_keeps_split(tmp_path) -> None:
    import cv2

    w = cv2.VideoWriter(str(tmp_path / "b.mp4"), cv2.VideoWriter_fourcc(*"mp4v"), 10, (160, 120))
    for _ in range(12):
        w.write(np.zeros((120, 160, 3), np.uint8))
    w.release()
    (tmp_path / "i.csv").write_text("video,label,signer_id,split\nb.mp4,HELLO,S1,train\n")
    written, skipped = process_videos(tmp_path / "i.csv", tmp_path / "out")
    assert written == 0 and len(skipped) == 1
    assert (tmp_path / "out" / "manifest.csv").read_text().strip() == "path,label,signer_id,split"
    assert "usable frame" in (tmp_path / "out" / "exclusions.csv").read_text()
