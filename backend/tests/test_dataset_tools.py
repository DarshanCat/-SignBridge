import json
from types import SimpleNamespace

import numpy as np
import pytest

from app.recognition.landmarks import FEATURE_DIM
from training.data import DatasetError
from training.dataset_info import read_dataset_info
from training.record_sample import append_sample
from training.validate_dataset import validate
from training.video_features import process_videos, results_to_frame, video_to_features
from tests.test_training_pipeline import make_dataset


def info(path, **kw) -> None:
    data = {"name": "t", "language": "ISL", "license": "CC BY 4.0", "source_url": "https://example.org", **kw}
    (path / "dataset_info.json").write_text(json.dumps(data))


def test_info_required_and_asl_rejected(tmp_path) -> None:
    with pytest.raises(DatasetError, match="not found"):
        read_dataset_info(tmp_path)
    info(tmp_path, language="ASL")
    with pytest.raises(DatasetError, match="only Indian Sign Language"):
        read_dataset_info(tmp_path)
    info(tmp_path, license="")
    with pytest.raises(DatasetError, match="missing values"):
        read_dataset_info(tmp_path)
    info(tmp_path, language="isl")
    assert read_dataset_info(tmp_path).language == "ISL"


def test_validate_ok_with_report(tmp_path) -> None:
    make_dataset(tmp_path, signers=4, per=5)
    report = validate(tmp_path)
    assert report["num_samples"] == 60 and report["num_classes"] == 3 and report["num_signers"] == 4
    assert report["warnings"] == []


def test_validate_warns_on_few_signers(tmp_path) -> None:
    make_dataset(tmp_path, signers=2, per=5)
    assert any("signer" in w for w in validate(tmp_path)["warnings"])


def test_validate_rejects_bad_features(tmp_path) -> None:
    make_dataset(tmp_path, signers=3, per=1)
    np.save(tmp_path / "s0_A_0.npy", np.zeros((5, 10), dtype=np.float32))
    with pytest.raises(DatasetError, match="bad shape"):
        validate(tmp_path)
    np.save(tmp_path / "s0_A_0.npy", np.full((5, FEATURE_DIM), np.nan, dtype=np.float32))
    with pytest.raises(DatasetError, match="non-finite"):
        validate(tmp_path)


def test_validate_requires_consent_when_flagged(tmp_path) -> None:
    make_dataset(tmp_path, signers=3, per=1)
    info(tmp_path, consent_required=True)
    with pytest.raises(DatasetError, match="consent.csv is required"):
        validate(tmp_path)
    (tmp_path / "consent.csv").write_text("signer_id,consent_date,scope\nsigner0,2026-01-01,research\n")
    with pytest.raises(DatasetError, match="No consent record"):
        validate(tmp_path)


def test_record_append_creates_consent_and_manifest(tmp_path) -> None:
    feats = np.zeros((10, FEATURE_DIM), dtype=np.float32)
    for _ in range(2):
        append_sample(tmp_path, feats, "HELLO", "S01", "research")
    append_sample(tmp_path, feats, "THANKS", "S02", "research")
    assert len((tmp_path / "manifest.csv").read_text().splitlines()) == 4
    assert len((tmp_path / "consent.csv").read_text().splitlines()) == 3  # header + 2 signers, once each
    assert read_dataset_info(tmp_path).consent_required
    assert validate(tmp_path)["num_samples"] == 3


def test_record_append_rejects_bad_input(tmp_path) -> None:
    with pytest.raises(DatasetError):
        append_sample(tmp_path, np.zeros((3, 4)), "A", "S1", "x")
    with pytest.raises(DatasetError):
        append_sample(tmp_path, np.zeros((3, FEATURE_DIM)), " ", "S1", "x")


def test_results_to_frame_handles_missing_parts() -> None:
    lm = SimpleNamespace(landmark=[SimpleNamespace(x=0.1, y=0.2, z=0.3)] * 33)
    frame = results_to_frame(SimpleNamespace(pose_landmarks=lm, left_hand_landmarks=None, right_hand_landmarks=None))
    assert len(frame.pose or []) == 33 and frame.left_hand is None


def _blank_video(path) -> None:
    import cv2

    w = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), 10, (160, 120))
    for _ in range(12):
        w.write(np.zeros((120, 160, 3), np.uint8))
    w.release()


def test_video_without_person_is_rejected(tmp_path) -> None:
    _blank_video(tmp_path / "blank.mp4")
    with pytest.raises(DatasetError, match="usable frame"):
        video_to_features(tmp_path / "blank.mp4")
    with pytest.raises(DatasetError, match="Cannot open"):
        video_to_features(tmp_path / "missing.mp4")


def test_process_videos_skips_unusable_and_writes_manifest(tmp_path) -> None:
    _blank_video(tmp_path / "blank.mp4")
    (tmp_path / "index.csv").write_text("video,label,signer_id\nblank.mp4,HELLO,S1\n")
    written, skipped = process_videos(tmp_path / "index.csv", tmp_path / "out")
    assert written == 0 and len(skipped) == 1
    assert (tmp_path / "out" / "manifest.csv").read_text().strip() == "path,label,signer_id"
    (tmp_path / "bad.csv").write_text("video,label\nx,y\n")
    with pytest.raises(DatasetError, match="needs columns"):
        process_videos(tmp_path / "bad.csv", tmp_path / "out2")
