"""End-to-end tests through the HTTP API for both workflows.

The recognition model here is trained on SYNTHETIC landmark sequences (class = hand position) that go through the real
normalization code. It verifies that the plumbing is correct, not that any real sign is recognized.
"""

import json
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.main import app
from app.recognition.landmarks import normalize_frame
from app.schemas.landmarks import LandmarkFrame
from tests.helpers import valid_clip
from tests.test_landmarks import hand, pose, pt
from training.train import train

client = TestClient(app)
CLASSES = ["HELLO", "WATER", "YES"]
EXPECTED_ENGLISH = {"HELLO": "Hello.", "WATER": "Water.", "YES": "Yes."}


def class_frames(k: int, rng: np.random.Generator, n: int = 12) -> list[dict]:
    """Landmark frames whose left hand sits at a class-specific x position (plus jitter)."""
    frames = []
    for _ in range(n):
        x = 0.2 + 0.15 * k + rng.normal(0, 0.005)
        frames.append({"pose": pose(), "left_hand": [pt(x + rng.normal(0, 0.002), 0.6)] * 21, "right_hand": None})
    return frames


def to_features(frames: list[dict]) -> np.ndarray:
    return np.stack([normalize_frame(LandmarkFrame.model_validate(f))[0] for f in frames])


@pytest.fixture(scope="module")
def model_dir(tmp_path_factory) -> Path:
    root = tmp_path_factory.mktemp("integration")
    rng = np.random.default_rng(0)
    rows = []
    for s in range(6):
        for k, c in enumerate(CLASSES):
            for i in range(4):
                name = f"s{s}_{c}_{i}.npy"
                np.save(root / name, to_features(class_frames(k, rng)))
                rows.append(f"{name},{c},signer{s}")
    (root / "manifest.csv").write_text("path,label,signer_id\n" + "\n".join(rows))
    (root / "dataset_info.json").write_text(
        '{"name":"synthetic-integration","language":"ISL","license":"n/a","source_url":"n/a"}'
    )
    out = root / "models"
    train(root / "manifest.csv", out, epochs=40, hidden=24, layers=1, patience=40)
    return out


def use(**kw) -> None:
    app.dependency_overrides[get_settings] = lambda: Settings(**kw)


def teardown_function() -> None:
    app.dependency_overrides.clear()


@pytest.mark.parametrize("k, label", list(enumerate(CLASSES)))
def test_sign_to_english_pipeline(model_dir, k, label) -> None:
    use(model_dir=model_dir, min_confidence=0.0)
    frames = class_frames(k, np.random.default_rng(99 + k))
    r = client.post("/api/signs/translate", json={"frames": frames})
    body = r.json()
    assert r.status_code == 200, body
    assert body["accepted"] and body["predictions"][0]["label"] == label
    assert body["gloss"] == [label] and body["english"] == EXPECTED_ENGLISH[label]
    # Round trip: the English we produced maps back to the same gloss.
    back = client.post("/api/translation/english-to-gloss", json={"text": body["english"]}).json()
    assert back["gloss"] == [label]


def test_low_confidence_prediction_is_rejected(model_dir) -> None:
    use(model_dir=model_dir, min_confidence=1.01)
    body = client.post("/api/signs/translate", json={"frames": class_frames(0, np.random.default_rng(1))}).json()
    assert body["accepted"] is False and body["gloss"] == [] and body["english"] == ""
    assert "below" in body["message"] and body["predictions"]


def test_label_outside_vocabulary_is_flagged(model_dir, tmp_path) -> None:
    cfg = tmp_path / "v.json"
    cfg.write_text(json.dumps({"glosses": {"WATER": {"english": "water", "words": ["water"]}}}))
    use(model_dir=model_dir, min_confidence=0.0, translation_config=cfg)
    body = client.post("/api/signs/translate", json={"frames": class_frames(0, np.random.default_rng(2))}).json()
    assert body["accepted"] and body["unsupported"] == ["HELLO"] and body["english"] == ""
    assert "not in the translation vocabulary" in body["message"]


def test_sign_to_english_errors(model_dir, tmp_path) -> None:
    use(model_dir=tmp_path / "none")
    r = client.post("/api/signs/translate", json={"frames": class_frames(0, np.random.default_rng(3))})
    assert r.status_code == 503 and "accepted" not in r.json()
    use(model_dir=model_dir)
    assert client.post("/api/signs/translate", json={"frames": class_frames(0, np.random.default_rng(3))[:2]}).status_code == 422
    assert client.post("/api/signs/translate", json={"frames": []}).status_code == 422
    use(model_dir=model_dir, translation_config=tmp_path / "missing.json")
    assert client.post("/api/signs/translate", json={"frames": class_frames(0, np.random.default_rng(3))}).status_code == 503


def test_english_to_avatar_pipeline_with_clips(tmp_path) -> None:
    anims = tmp_path / "anims"
    anims.mkdir()
    for g in ("HELLO", "WATER"):
        (anims / f"{g.lower()}.json").write_text(json.dumps(valid_clip(g)))
    use(animation_dir=anims)

    g = client.post("/api/translation/english-to-gloss", json={"text": "Hello, water please"}).json()
    plan = client.post("/api/avatar/plan", json={"gloss": g["gloss"]}).json()
    assert g["gloss"] == ["HELLO", "WATER"] and plan["playable"] is True
    assert [s["clip_url"] for s in plan["steps"]] == ["/animations/hello.json", "/animations/water.json"]

    mixed = client.post("/api/translation/english-to-gloss", json={"text": "hello food quantum"}).json()
    plan2 = client.post("/api/avatar/plan", json={"gloss": mixed["gloss"]}).json()
    assert mixed["unsupported"] == ["quantum"] and plan2["missing"] == ["FOOD"] and plan2["playable"] is False


def test_response_includes_processing_time_header() -> None:
    r = client.get("/api/health")
    assert float(r.headers["x-process-time-ms"]) >= 0
