"""Phase 3 code tests on SYNTHETIC tensors only. They verify behaviour of the code, not recognition quality."""

import json

import numpy as np
import pytest
import torch

from app.recognition.artifacts import ModelConfig, load_artifacts, save_artifacts
from app.recognition.inference import UNRECOGNIZED, Prediction, SignRecognizer, label_or_unrecognized
from app.recognition.landmarks import FEATURE_DIM, normalize_frame
from app.recognition.models import ARCHITECTURES, CNN1DClassifier, TransformerClassifier, build_model
from app.recognition.preprocess import fill_hand_gaps, hand_missing_mask, prepare_sequence, resample_sequence
from app.schemas.landmarks import LandmarkFrame
from tests.test_landmarks import hand, pose
from tests.test_training_pipeline import make_dataset
from training.augment import AugmentConfig, augment_sequence, rotate_xy, speed_resample, time_jitter
from training.compare_models import pick_best, results_markdown
from training.dataset import load_splits
from training.evaluate import evaluate, to_markdown
from training.slr_metrics import coverage_curve, per_class_accuracy, topk_accuracy
from training.train import train

POSE_END, LEFT_END = 99, 162


def seq(t: int = 20, seed: int = 0) -> np.ndarray:
    return np.random.default_rng(seed).normal(0, 0.5, (t, FEATURE_DIM)).astype(np.float32)


# normalization and missing-hand handling -------------------------------------------------------------------------------

def test_normalization_origin_scale_and_missing_hand() -> None:
    f, rep = normalize_frame(LandmarkFrame.model_validate({"pose": pose(0.7, 0.4), "left_hand": hand(0.5), "right_hand": None}))
    mid = (f[11 * 3 : 11 * 3 + 3] + f[12 * 3 : 12 * 3 + 3]) / 2
    assert np.allclose(mid, 0, atol=1e-6)  # shoulder midpoint is the origin
    assert np.isclose(np.linalg.norm(f[11 * 3 : 11 * 3 + 2] - f[12 * 3 : 12 * 3 + 2]), 1.0, atol=1e-5)  # shoulder width is 1
    assert not f[LEFT_END:].any() and rep.has_left_hand and not rep.has_right_hand


def test_hand_missing_mask_and_gap_fill() -> None:
    x = np.ones((10, FEATURE_DIM), dtype=np.float32)
    x[3:5, POSE_END:LEFT_END] = 0  # left hand missing for 2 frames (inside)
    x[0, LEFT_END:] = 0  # right hand missing at the start
    x[6:9, LEFT_END:] = 0  # right hand missing for 3 frames (inside)
    left, right = hand_missing_mask(x)
    assert left.sum() == 2 and right.sum() == 4
    assert np.array_equal(fill_hand_gaps(x, 0), x)  # off by default
    y = fill_hand_gaps(x, 2)
    assert y[3:5, POSE_END:LEFT_END].all()  # short gap interpolated
    assert not y[0, LEFT_END:].any()  # leading gap stays zero
    assert not y[6:9, LEFT_END:].any()  # gap longer than max_gap stays zero
    assert fill_hand_gaps(x, 3)[6:9, LEFT_END:].all()
    assert np.allclose(y[3, POSE_END:LEFT_END], 1.0)  # interpolation between equal neighbours


def test_gap_fill_interpolates_linearly() -> None:
    x = np.zeros((5, FEATURE_DIM), dtype=np.float32)
    x[0, LEFT_END:] = 0.0
    x[:, POSE_END:LEFT_END] = np.array([1, 0, 0, 0, 3], dtype=np.float32)[:, None]
    x[1:4, POSE_END:LEFT_END] = 0
    y = fill_hand_gaps(x, 5)
    assert np.allclose(y[:, POSE_END], [1, 1.5, 2, 2.5, 3])


def test_resample_and_prepare_shapes_and_errors() -> None:
    assert prepare_sequence(seq(7), 32).shape == (32, FEATURE_DIM)
    assert prepare_sequence(seq(50), 32, max_gap=3).dtype == np.float32
    assert np.array_equal(prepare_sequence(seq(32), 32), resample_sequence(seq(32), 32))
    with pytest.raises(ValueError):
        resample_sequence(np.zeros((0, FEATURE_DIM)), 8)


# augmentation ---------------------------------------------------------------------------------------------------------

def test_augmentation_is_reproducible_and_changes_data() -> None:
    x = seq(30)
    a = augment_sequence(x, np.random.default_rng(1))
    b = augment_sequence(x, np.random.default_rng(1))
    c = augment_sequence(x, np.random.default_rng(2))
    assert np.array_equal(a, b) and not np.array_equal(a, c) and a.dtype == np.float32 and a.shape[1] == FEATURE_DIM
    with pytest.raises(ValueError):
        augment_sequence(np.zeros((5, 10)), np.random.default_rng(0))


def test_rotation_scale_keep_missing_hands_zero_and_are_invertible() -> None:
    x = seq(12)
    x[:, LEFT_END:] = 0
    r = rotate_xy(x, 10.0)
    assert not r[:, LEFT_END:].any() and not np.allclose(r, x)
    assert np.allclose(rotate_xy(r, -10.0), x, atol=1e-5)
    assert np.array_equal(rotate_xy(x, 0.0), x)
    assert np.allclose(np.linalg.norm(r.reshape(12, -1, 3)[..., :2], axis=-1), np.linalg.norm(x.reshape(12, -1, 3)[..., :2], axis=-1), atol=1e-5)


def test_speed_and_temporal_jitter() -> None:
    x = seq(40)
    assert speed_resample(x, 2.0).shape[0] == 20 and speed_resample(x, 0.5).shape[0] == 80 and speed_resample(seq(5), 10).shape[0] == 4
    j = time_jitter(x, np.random.default_rng(0), AugmentConfig())
    assert j.shape == x.shape and np.isfinite(j).all()


def test_augment_probability_zero_is_identity() -> None:
    cfg = AugmentConfig(p_rotate=0, p_scale=0, p_speed=0, p_jitter=0)
    x = seq(15)
    assert np.array_equal(augment_sequence(x, np.random.default_rng(0), cfg), x)


# models ---------------------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("arch", ARCHITECTURES)
def test_every_architecture_forward_backward_and_artifact_round_trip(arch, tmp_path) -> None:
    cfg = ModelConfig(["a", "b", "c"], FEATURE_DIM, 16, hidden=16, layers=1, dropout=0.1, arch=arch, heads=2, max_gap=2)
    model = build_model(cfg)
    x = torch.randn(4, 16, FEATURE_DIM)
    out = model(x)
    assert out.shape == (4, 3)
    out.sum().backward()
    save_artifacts(model, cfg, tmp_path)
    loaded, cfg2 = load_artifacts(tmp_path)
    assert cfg2 == cfg and loaded.training is False
    assert torch.allclose(loaded(x), model.eval()(x), atol=1e-6)


def test_model_factory_errors_and_transformer_limits() -> None:
    with pytest.raises(ValueError, match="unknown architecture"):
        build_model(ModelConfig(["a", "b"], FEATURE_DIM, 8, arch="lstm"))
    with pytest.raises(ValueError, match="divisible"):
        TransformerClassifier(FEATURE_DIM, 2, hidden=10, heads=4)
    with pytest.raises(ValueError, match="exceeds"):
        TransformerClassifier(FEATURE_DIM, 2, hidden=8, heads=2, max_len=4)(torch.zeros(1, 9, FEATURE_DIM))
    assert CNN1DClassifier(FEATURE_DIM, 5, hidden=8)(torch.zeros(2, 12, FEATURE_DIM)).shape == (2, 5)


def test_old_labels_json_without_new_fields_still_loads(tmp_path) -> None:
    cfg = ModelConfig(["a", "b"], FEATURE_DIM, 8, hidden=8, layers=1)
    save_artifacts(build_model(cfg), cfg, tmp_path)
    raw = json.loads((tmp_path / "labels.json").read_text())
    for k in ("arch", "heads", "max_gap"):
        raw.pop(k)
    (tmp_path / "labels.json").write_text(json.dumps(raw))
    _, loaded = load_artifacts(tmp_path)
    assert loaded.arch == "bigru" and loaded.max_gap == 0


# metrics, inference function --------------------------------------------------------------------------------------------

def test_topk_per_class_and_coverage_on_known_probabilities() -> None:
    probs = np.array([[0.7, 0.2, 0.1], [0.4, 0.5, 0.1], [0.1, 0.2, 0.7], [0.40, 0.35, 0.25]])
    y = np.array([0, 0, 1, 2])
    assert topk_accuracy(probs, y, 1) == 0.25 and topk_accuracy(probs, y, 2) == 0.75 and topk_accuracy(probs, y, 5) == 1.0
    pc = per_class_accuracy(probs.argmax(axis=1), y, ["a", "b", "c", "d"])
    assert pc["a"]["accuracy"] == 0.5 and pc["d"] == {"support": 0, "accuracy": None}
    curve = coverage_curve(probs, y, thresholds=(0.0, 0.5, 0.75))
    assert [c["coverage"] for c in curve] == [1.0, 0.75, 0.0]
    assert curve[1]["accuracy_on_answered"] == pytest.approx(1 / 3) and curve[2]["accuracy_on_answered"] is None
    assert curve[1]["unrecognized"] == 1 and curve[0]["answered"] == 4


def test_label_or_unrecognized() -> None:
    preds = [Prediction("HELLO", 0.62), Prediction("WATER", 0.2)]
    assert label_or_unrecognized(preds, 0.5) == "HELLO"
    assert label_or_unrecognized(preds, 0.7) == UNRECOGNIZED
    assert label_or_unrecognized([], 0.1) == UNRECOGNIZED


@pytest.mark.parametrize("arch", ARCHITECTURES)
def test_recognizer_predict_uses_the_shared_preprocessing(arch) -> None:
    cfg = ModelConfig(["a", "b", "c"], FEATURE_DIM, 12, hidden=8, layers=1, arch=arch, heads=2, max_gap=3)
    model = build_model(cfg).eval()
    rec = SignRecognizer(model, cfg)
    x = seq(25)
    x[4:6, POSE_END:LEFT_END] = 0
    preds = rec.predict(x, top_k=3)
    manual = torch.softmax(model(torch.from_numpy(prepare_sequence(x, 12, 3)).unsqueeze(0)), dim=-1)[0]
    assert abs(sum(p.confidence for p in preds) - 1.0) < 1e-5
    assert preds[0].confidence == pytest.approx(float(manual.max()), abs=1e-6)


# loader, training, evaluation, comparison -------------------------------------------------------------------------------

def test_loader_reads_manifest_path_and_augments_per_call(tmp_path) -> None:
    m = make_dataset(tmp_path)
    data = load_splits(m, seed=0)
    assert set(data.stores) == {"train", "val", "test"} and data.method == "signer-disjoint" and len(data.classes) == 3
    tr = data.stores["train"]
    idx = np.arange(4)
    plain = tr.batch(idx, 16)
    assert plain.shape == (4, 16, FEATURE_DIM) and np.array_equal(plain, tr.batch(idx, 16))
    a = tr.batch(idx, 16, rng=np.random.default_rng(0), augment=AugmentConfig())
    b = tr.batch(idx, 16, rng=np.random.default_rng(0), augment=AugmentConfig())
    assert np.array_equal(a, b) and not np.array_equal(a, plain)


@pytest.mark.parametrize("arch", ARCHITECTURES)
def test_train_smoke_each_architecture_then_evaluate_held_out_test(arch, tmp_path) -> None:
    m = make_dataset(tmp_path)
    out = tmp_path / "m"
    rep = train(m, out, arch=arch, epochs=1, hidden=8, layers=1, heads=2, seq_len=12, augment=True, max_gap=2, num_threads=1)
    t = rep["results"]["test"]
    for key in ("top1_accuracy", "top5_accuracy", "macro_f1", "per_class_accuracy", "accuracy_vs_coverage", "confusion_matrix"):
        assert key in t
    assert rep["hyperparameters"]["arch"] == arch and rep["parameters"] > 0 and rep["hyperparameters"]["epochs_run"] == 1
    ev = evaluate(m, out)
    assert ev["architecture"] == arch and ev["num_test_samples"] == rep["sample_counts"]["test"]
    assert ev["top1_accuracy"] == pytest.approx(t["top1_accuracy"]) and ev["confusion_matrix"] == t["confusion_matrix"]
    assert "Accuracy versus coverage" in to_markdown(ev)


def test_compare_models_picks_best_by_validation_not_test() -> None:
    def rep(val, test):
        full = {"macro_f1": val, "top1_accuracy": 0, "top5_accuracy": 0, "macro_precision": 0, "macro_recall": 0, "accuracy_vs_coverage": []}
        return {"results": {"val": {**full, "macro_f1": val}, "test": {**full, "macro_f1": test}}, "parameters": 1,
                "hyperparameters": {"epochs_run": 1, "seed": 0}, "split_method": "predefined", "sample_counts": {}, "dataset": {"name": "n", "license": "l"},
                "classes_missing_from_train": []}
    reports = {"cnn": rep(0.5, 0.9), "bigru": rep(0.7, 0.1), "transformer": rep(0.6, 0.95)}
    assert pick_best(reports) == "bigru"  # highest validation score, although another model has a better test score
    assert "Best by validation macro-F1: **bigru**" in results_markdown(reports, "bigru")


def test_results_markdown_has_label_per_class_confusions_and_threshold(tmp_path) -> None:
    from training.calibrate import choose_threshold
    from training.compare_models import confusion_csv

    cm = [[3, 1], [2, 4]]
    t = {"macro_f1": 0.5, "top1_accuracy": 0.7, "top5_accuracy": 0.9, "macro_precision": 0.5, "macro_recall": 0.5, "confusion_matrix": cm,
         "per_class_accuracy": {"A": {"support": 4, "accuracy": 0.75}, "B": {"support": 6, "accuracy": 0.667}},
         "accuracy_vs_coverage": [{"threshold": 0.5, "coverage": 0.8, "accuracy_on_answered": 0.9, "answered": 8, "unrecognized": 2}]}
    rep = {"results": {"val": {**t, "macro_f1": 0.6}, "test": t}, "parameters": 1, "hyperparameters": {"epochs_run": 1, "seed": 0},
           "split_method": "predefined", "sample_counts": {}, "dataset": {"name": "n", "license": "l"}, "classes_missing_from_train": []}
    md = results_markdown({"cnn": rep}, "cnn", {"cnn": "confusion_matrix_cnn.csv"},
                          {"threshold": 0.5, "rule": "r", "val_coverage": 0.7, "val_accuracy_on_answered": 0.95}, ["A", "B"])
    assert "Authors' predefined split, signer independence not verified." in md
    assert "| A | 4 | 0.750 |" in md and "| B | A | 2 |" in md and "**0.5**" in md and "coverage 0.8000 and accuracy on answered 0.9000" in md and "confusion_matrix_cnn.csv" in md
    confusion_csv(t, ["A", "B"], tmp_path / "c.csv")
    assert (tmp_path / "c.csv").read_text().splitlines()[1] == "A,3,1"
    probs = np.array([[0.9, 0.1], [0.6, 0.4], [0.55, 0.45], [0.2, 0.8], [0.3, 0.7], [0.95, 0.05]] * 4)
    y = np.array([0, 1, 1, 1, 0, 0] * 4)
    assert 0.0 <= choose_threshold(probs, y, 0.9) <= 0.95
