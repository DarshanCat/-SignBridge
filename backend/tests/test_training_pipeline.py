"""Mechanics tests for preprocessing, metrics, splitting, training and inference.

The models trained here use synthetic arrays in tmp dirs purely to exercise the code; they say
nothing about real sign-recognition accuracy and are never written to backend/models.
"""

import csv
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.main import app
from app.recognition.artifacts import ModelLoadError, load_artifacts
from app.recognition.inference import get_recognizer
from app.recognition.landmarks import FEATURE_DIM
from app.recognition.model_status import get_model_status
from app.recognition.preprocess import resample_sequence
from tests.test_landmarks import frame
from training.data import DatasetError, read_manifest, split_by_signer
from training.metrics import classification_report
from training.train import train

client = TestClient(app)
CLASSES = ["A", "B", "C"]


def make_dataset(root: Path, signers: int = 6, per: int = 4, classes: list[str] | None = None) -> Path:
    classes = classes or CLASSES
    rng = np.random.default_rng(0)
    rows = []
    for s in range(signers):
        for ci, c in enumerate(classes):
            for k in range(per):
                arr = rng.normal(0, 0.05, (20, FEATURE_DIM)).astype(np.float32)
                arr[:, ci * 10 : ci * 10 + 10] += 1.0  # class-specific pattern
                name = f"s{s}_{c}_{k}.npy"
                np.save(root / name, arr)
                rows.append([name, c, f"signer{s}"])
    (root / "dataset_info.json").write_text(
        '{"name":"synthetic-test","language":"ISL","license":"n/a","source_url":"n/a"}'
    )
    manifest = root / "manifest.csv"
    with manifest.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["path", "label", "signer_id"])
        w.writerows(rows)
    return manifest


@pytest.fixture(scope="module")
def trained(tmp_path_factory) -> Path:
    root = tmp_path_factory.mktemp("ds")
    out = root / "models"
    train(make_dataset(root), out, epochs=15, hidden=16, layers=1, patience=15)
    return out


def teardown_function() -> None:
    app.dependency_overrides.clear()


def test_resample_shapes_and_errors() -> None:
    assert resample_sequence(np.zeros((7, FEATURE_DIM)), 32).shape == (32, FEATURE_DIM)
    assert resample_sequence(np.zeros((40, FEATURE_DIM)), 32).shape == (32, FEATURE_DIM)
    with pytest.raises(ValueError):
        resample_sequence(np.zeros((5, 10)), 32)


def test_metrics_known_values() -> None:
    rep = classification_report(np.array([0, 0, 1, 1]), np.array([0, 1, 1, 1]), ["a", "b"])
    assert rep["accuracy"] == 0.75
    assert rep["per_class"]["a"]["recall"] == 0.5
    assert rep["confusion_matrix"] == [[1, 1], [0, 2]]
    assert round(rep["macro_f1"], 3) == round((2 / 3 + 0.8) / 2, 3)


def test_split_is_signer_disjoint(tmp_path) -> None:
    samples = read_manifest(make_dataset(tmp_path, signers=6))
    sp = split_by_signer(samples, seed=1)
    sets = {k: {s.signer for s in v} for k, v in sp.items()}
    assert not (sets["train"] & sets["val"]) and not (sets["train"] & sets["test"]) and not (sets["val"] & sets["test"])
    assert all(sets.values())


def test_split_refuses_too_few_signers(tmp_path) -> None:
    samples = read_manifest(make_dataset(tmp_path, signers=2))
    with pytest.raises(DatasetError, match="at least 3 signers"):
        split_by_signer(samples, seed=0)


def test_manifest_errors(tmp_path) -> None:
    with pytest.raises(DatasetError, match="not found"):
        read_manifest(tmp_path / "nope.csv")
    bad = tmp_path / "m.csv"
    bad.write_text("path,label\nx.npy,A\n")
    with pytest.raises(DatasetError, match="missing columns"):
        read_manifest(bad)
    bad.write_text("path,label,signer_id\nmissing.npy,A,s1\n")
    with pytest.raises(DatasetError, match="not found"):
        read_manifest(bad)


def test_training_writes_artifacts_and_metrics(trained: Path) -> None:
    for name in ("isl_model.pt", "labels.json", "metrics.json"):
        assert (trained / name).is_file()
    model, config = load_artifacts(trained)
    assert config.classes == CLASSES and config.feature_dim == FEATURE_DIM


def test_inference_returns_valid_probabilities(trained: Path) -> None:
    preds = get_recognizer(trained).predict(np.random.default_rng(1).normal(size=(12, FEATURE_DIM)).astype(np.float32))
    assert len(preds) == 3 and all(0 <= p.confidence <= 1 for p in preds)
    assert preds[0].confidence >= preds[1].confidence


def test_status_loaded_error_and_untrained(trained: Path, tmp_path) -> None:
    assert get_model_status(trained).state == "loaded"
    assert get_model_status(tmp_path).state == "not_trained"
    broken = tmp_path / "broken"
    broken.mkdir()
    (broken / "isl_model.pt").write_bytes(b"junk")
    (broken / "labels.json").write_text("{}")
    assert get_model_status(broken).state == "error"
    with pytest.raises(ModelLoadError):
        get_recognizer(broken)


def _use(model_dir: Path) -> None:
    app.dependency_overrides[get_settings] = lambda: Settings(model_dir=model_dir)


def test_recognize_503_without_model(tmp_path) -> None:
    _use(tmp_path)
    r = client.post("/api/signs/recognize", json={"frames": [frame()] * 10})
    assert r.status_code == 503 and "predictions" not in r.json()


def test_recognize_with_model(trained: Path) -> None:
    _use(trained)
    r = client.post("/api/signs/recognize", json={"frames": [frame()] * 10})
    body = r.json()
    assert r.status_code == 200 and body["num_frames_used"] == 10
    assert {p["label"] for p in body["predictions"]} <= set(CLASSES)


def test_recognize_422_for_unusable_sequence(trained: Path) -> None:
    _use(trained)
    assert client.post("/api/signs/recognize", json={"frames": [frame()]}).status_code == 422


def _ck(out: Path, name: str = "checkpoint_last.pt") -> dict:
    import torch

    return torch.load(out / name, map_location="cpu", weights_only=False)


def test_checkpoint_resume_continues_the_same_run(tmp_path):
    ds = make_dataset(tmp_path)
    kw = dict(hidden=16, layers=1, patience=50, num_threads=1, max_gap=3, deploy_augment=True, checkpoint=True)
    straight = tmp_path / "straight"
    train(ds, straight, epochs=4, **kw)
    split = tmp_path / "split"
    train(ds, split, epochs=2, **kw)  # "killed" after epoch 2: only the checkpoint of epoch 2 matters
    assert _ck(split)["epochs_run"] == 2
    resumed = train(ds, split, epochs=4, resume=True, **kw)
    assert resumed["hyperparameters"]["epochs_run"] == 4
    a, b = _ck(straight), _ck(split)
    assert a["epochs_run"] == b["epochs_run"] == 4
    for k in a["model"]:
        np.testing.assert_allclose(a["model"][k].numpy(), b["model"][k].numpy(), atol=1e-6)
    assert a["best_f1"] == pytest.approx(b["best_f1"])
    assert (split / "checkpoint_best.pt").is_file()
    assert not list(split.glob("*.tmp"))  # atomic writes leave no temporary file


def test_resume_of_a_finished_run_changes_nothing(tmp_path):
    ds = make_dataset(tmp_path)
    kw = dict(hidden=16, layers=1, patience=50, num_threads=1, checkpoint=True)
    first = train(ds, tmp_path / "m", epochs=3, **kw)
    again = train(ds, tmp_path / "m", epochs=3, resume=True, **kw)
    assert again["hyperparameters"]["epochs_run"] == 3
    assert again["results"]["val"]["macro_f1"] == pytest.approx(first["results"]["val"]["macro_f1"])


def test_resume_refuses_missing_or_changed_settings(tmp_path):
    ds = make_dataset(tmp_path)
    with pytest.raises(DatasetError, match="nothing to resume"):
        train(ds, tmp_path / "none", epochs=2, hidden=16, layers=1, resume=True)
    train(ds, tmp_path / "m", epochs=2, hidden=16, layers=1, checkpoint=True, num_threads=1)
    with pytest.raises(DatasetError, match="hidden"):
        train(ds, tmp_path / "m", epochs=4, hidden=32, layers=1, resume=True, num_threads=1)
    with pytest.raises(DatasetError, match="deploy_augment"):
        train(ds, tmp_path / "m", epochs=4, hidden=16, layers=1, resume=True, deploy_augment=True, num_threads=1)


def test_training_without_checkpoint_writes_none(tmp_path):
    train(make_dataset(tmp_path), tmp_path / "m", epochs=2, hidden=16, layers=1)
    assert not (tmp_path / "m" / "checkpoint_last.pt").exists()
