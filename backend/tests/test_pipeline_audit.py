"""Phase 9 audit tests: model loading, caching, feature-dimension guards and preprocessing consistency.

Models here are trained on SYNTHETIC arrays to exercise the code paths; they are not evidence of ISL recognition.
"""

import json
import os
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.main import app
from app.recognition.artifacts import ModelLoadError, load_artifacts
from app.recognition.inference import get_recognizer
from app.recognition.landmarks import FEATURE_DIM, normalize_frame, process_sequence
from app.recognition.model_status import get_model_status
from app.recognition.preprocess import resample_sequence
from app.schemas.landmarks import LandmarkFrame, LandmarkSequenceRequest
from tests.test_landmarks import frame, pose, pt
from tests.test_training_pipeline import trained  # noqa: F401  (fixture)
from training.data import Sample, load_arrays

client = TestClient(app)


def teardown_function() -> None:
    app.dependency_overrides.clear()


def _use(model_dir: Path) -> None:
    app.dependency_overrides[get_settings] = lambda: Settings(model_dir=model_dir)


def varied_frames(n: int = 20) -> list[dict]:
    rng = np.random.default_rng(5)
    return [
        {"pose": pose(), "left_hand": [pt(0.3 + rng.normal(0, 0.01), 0.6)] * 21, "right_hand": None} for _ in range(n)
    ]


def test_model_loaded_once_and_reloaded_only_on_change(trained, tmp_path) -> None:  # noqa: F811
    first = get_recognizer(trained)
    assert get_recognizer(trained) is first
    st = (trained / "isl_model.pt").stat()
    os.utime(trained / "isl_model.pt", ns=(st.st_atime_ns, st.st_mtime_ns + 5_000_000_000))
    assert get_recognizer(trained) is not first


def test_lifespan_starts_with_and_without_model() -> None:
    with TestClient(app) as c:  # runs the startup hook, which must not fail with no model
        assert c.get("/api/health").status_code == 200


def test_feature_dim_mismatch_is_a_load_error(trained, tmp_path) -> None:  # noqa: F811
    bad = tmp_path / "m"
    bad.mkdir()
    (bad / "isl_model.pt").write_bytes((trained / "isl_model.pt").read_bytes())
    cfg = json.loads((trained / "labels.json").read_text())
    cfg["feature_dim"] = 99
    (bad / "labels.json").write_text(json.dumps(cfg))
    with pytest.raises(ModelLoadError, match="99 features"):
        load_artifacts(bad)
    assert get_model_status(bad).state == "error"
    _use(bad)
    assert client.post("/api/signs/recognize", json={"frames": varied_frames()}).status_code == 503


def test_recognizer_rejects_wrong_feature_dimension(trained) -> None:  # noqa: F811
    with pytest.raises(ValueError):
        get_recognizer(trained).predict(np.zeros((10, FEATURE_DIM - 1), dtype=np.float32))


@pytest.mark.parametrize(
    "frames",
    [
        [{"pose": None, "left_hand": None, "right_hand": None}] * 12,  # tracking never valid
        [frame()] * 3,  # too short
        [{"pose": pose()[:5], "left_hand": None, "right_hand": None}] * 12,  # malformed landmark count
    ],
)
def test_recognize_rejects_unusable_sequences(trained, frames) -> None:  # noqa: F811
    _use(trained)
    assert client.post("/api/signs/recognize", json={"frames": frames}).status_code == 422


def test_recognize_rejects_oversized_and_malformed_requests(trained) -> None:  # noqa: F811
    _use(trained)
    assert client.post("/api/signs/recognize", json={"frames": [frame()] * 301}).status_code == 422
    assert client.post("/api/signs/recognize", json={"frames": [{"pose": [{"x": "a"}]}]}).status_code == 422
    assert client.post("/api/signs/recognize", content=b"nope").status_code == 422


def test_api_features_equal_per_frame_normalization() -> None:
    frames = varied_frames(10)
    api = process_sequence(LandmarkSequenceRequest(frames=[LandmarkFrame.model_validate(f) for f in frames]))
    direct = np.stack([normalize_frame(LandmarkFrame.model_validate(f))[0] for f in frames])
    assert np.allclose(np.array(api.features, dtype=np.float32), direct, atol=1e-6)


def test_training_and_inference_paths_produce_identical_model_input(trained, tmp_path) -> None:  # noqa: F811
    """The array the trainer would feed the model equals the array inference feeds it for the same landmarks."""
    frames = varied_frames(25)
    feats = np.array(
        process_sequence(LandmarkSequenceRequest(frames=[LandmarkFrame.model_validate(f) for f in frames])).features,
        dtype=np.float32,
    )
    npy = tmp_path / "s.npy"
    np.save(npy, feats)
    rec = get_recognizer(trained)
    x_train, _ = load_arrays([Sample(npy, rec.config.classes[0], "s1")], rec.config.classes, rec.config.seq_len)
    x_infer = resample_sequence(feats, rec.config.seq_len)
    assert np.array_equal(x_train[0], x_infer)

    _use(trained)
    api = client.post("/api/signs/recognize", json={"frames": frames}).json()
    direct = rec.predict(feats)
    assert api["predictions"][0]["label"] == direct[0].label
    assert api["predictions"][0]["confidence"] == pytest.approx(direct[0].confidence, abs=1e-6)
