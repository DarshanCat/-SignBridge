"""Tests for the INCLUDE streaming helpers (no network, no real videos)."""

import csv
import json

from training.dataset_info import read_dataset_info
from training.include_stream import finalize, label_of, load_splits
from training.validate_dataset import validate


def test_label_of_strips_the_numeric_prefix() -> None:
    assert label_of("Greetings/48. Hello/MVI_0089.MOV") == "Hello"
    assert label_of("Animals/4. Bird/x.MP4") == "Bird"
    assert label_of("Cat/Unnumbered/x.MOV") == "Unnumbered"
    assert label_of("Animals/4. Bird/Extra/MVI_3042.MOV") == "Bird"  # nested Extra folder belongs to the parent class


def test_load_splits_keeps_only_video_lines_case_insensitively(tmp_path) -> None:
    d = tmp_path / "splits"
    d.mkdir()
    (d / "include_train.txt").write_text("Places/23. Court/MVI_3612.MOV\nPlaces/23. Court/\n")
    (d / "include_val.txt").write_text("Animals/4. Bird/MVI_3040.mp4\n")
    (d / "include_test.txt").write_text("")
    s = load_splits(d)
    assert s == {"places/23. court/mvi_3612.mov": "train", "animals/4. bird/mvi_3040.mp4": "val"}


def test_finalize_writes_valid_manifest_and_provenance(tmp_path) -> None:
    import numpy as np

    from app.recognition.landmarks import FEATURE_DIM

    out = tmp_path / "out"
    (out / "_parts").mkdir(parents=True)
    rows = []
    for i, (cat, label, split) in enumerate([("A", "Hello", "train"), ("B", "Hello", "val"), ("A", "Bird", "test")]):
        np.save(out / f"{i}.npy", np.ones((10, FEATURE_DIM), dtype=np.float32) * i)
        rows.append({"member": f"{cat}/{label}/{i}.MOV", "npy": f"{i}.npy", "message": "", "split": split, "label": label, "category": cat})
    rows.append({"member": "A/Bad/9.MOV", "npy": "", "message": "only 2 usable frame(s)", "split": "train", "label": "Bad", "category": "A"})
    with (out / "_parts" / "z.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    finalize(out)

    manifest = list(csv.DictReader((out / "manifest.csv").open()))
    assert {r["label"] for r in manifest} == {"A/Hello", "B/Hello", "Bird"}  # a label used in two categories is disambiguated
    assert all(r["signer_id"] == "unknown" for r in manifest)
    assert "only 2 usable" in (out / "exclusions.csv").read_text()
    info = read_dataset_info(out)
    assert info.language == "ISL" and "CC BY 4.0" in info.license
    assert "unverified" in json.loads((out / "dataset_info.json").read_text())["notes"]
    report = validate(out)
    assert report["predefined_split"] is True and report["num_samples"] == 3


def test_verify_include_split_flags_missing_and_mismatched(tmp_path) -> None:
    from training.verify_include_split import verify

    raw, out = tmp_path / "raw", tmp_path / "out"
    (raw / "splits").mkdir(parents=True)
    (out / "_parts").mkdir(parents=True)
    (raw / "splits" / "include_train.txt").write_text("A/1. X/a.MOV\nA/1. X/b.MOV\n")
    (raw / "splits" / "include_val.txt").write_text("A/2. Y/c.MOV\n")
    (raw / "splits" / "include_test.txt").write_text("A/2. Y/d.MOV\nA/1. X/a.MOV\n")  # a.MOV is listed in two splits
    fields = ["member", "npy", "message", "split", "label", "category"]
    with (out / "_parts" / "z.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerow(dict(member="A/1. X/a.MOV", npy="1.npy", message="", split="test", label="X", category="A"))
        w.writerow(dict(member="A/1. X/b.MOV", npy="", message="only 1 usable frame(s)", split="train", label="X", category="A"))
        w.writerow(dict(member="A/9. Z/extra.MOV", npy="2.npy", message="", split="train", label="Z", category="A"))
    r = verify(raw, out, expected_zips=2)
    problems = " | ".join(r["problems"])
    assert "1 of 2 zip parts" in problems and "more than one split" in problems and "were not found" in problems
    assert r["per_split"]["train"]["excluded"] == 1 and r["processed_but_not_in_lists"] == 1
    assert r["signer_ids_available"] is False and "UNVERIFIED" in r["signer_independence"]
