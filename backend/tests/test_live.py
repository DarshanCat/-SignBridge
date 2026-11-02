"""Live WebSocket recognition: preprocessing must equal the training path exactly. Models here are tiny synthetic ones (mechanics only)."""

import json

import numpy as np
import pytest
import torch
from fastapi.testclient import TestClient

from app.api import nlp_routes
from app.core.config import Settings
from app.main import app
from app.recognition.inference import get_recognizer
from app.recognition.landmarks import normalize_frame
from app.recognition.preprocess import prepare_sequence
from app.schemas.landmarks import LandmarkFrame
from tests.test_landmarks import frame
from tests.test_training_pipeline import make_dataset
from training.dataset import SequenceStore
from training.train import train

client = TestClient(app)


def frames(n: int = 24, drop_pose_at: tuple[int, ...] = ()) -> list[dict]:
    out = []
    for t in range(n):
        f = frame()
        for p in f["pose"]:  # a moving wrist so frames differ
            pass
        f["pose"] = [dict(p) for p in f["pose"]]
        f["pose"][16] = {"x": 0.3 + 0.01 * t, "y": 0.5, "z": 0.0}
        f["right_hand"] = [{"x": 0.3 + 0.01 * t, "y": 0.55, "z": 0.0}] * 21 if t % 3 else None
        if t in drop_pose_at:
            f["pose"] = None
        out.append(f)
    return out


@pytest.fixture(scope="module")
def model_dir(tmp_path_factory):
    root = tmp_path_factory.mktemp("live")
    m = make_dataset(root)
    out = root / "model"
    train(m, out, arch="cnn", epochs=1, hidden=8, layers=1, seq_len=12, max_gap=2, num_threads=1)
    return out


@pytest.fixture
def served(model_dir, monkeypatch):
    monkeypatch.setattr(nlp_routes, "get_settings", lambda: Settings(model_dir=model_dir, min_confidence=0.0))
    return model_dir


def test_live_preprocessing_matches_training_exactly(served) -> None:
    fr = frames(30, drop_pose_at=(4, 5))
    with client.websocket_connect("/ws/predict") as ws:
        ready = ws.receive_json()
        assert ready["type"] == "ready" and ready["classes"] == 3
        ws.send_json({"type": "predict", "frames": fr})
        live = ws.receive_json()
    rec = get_recognizer(served)
    cfg = rec.config
    # the training path: normalize_frame per frame, keep valid frames, then prepare_sequence with the model's own seq_len and max_gap
    rows = [normalize_frame(LandmarkFrame(**f)) for f in fr]
    feats = np.array([r for r, rep in rows if rep.valid], dtype=np.float32)
    assert len(feats) == 28 and live["num_frames_used"] == 28
    x = prepare_sequence(feats, cfg.seq_len, cfg.max_gap)
    assert np.array_equal(x, SequenceStore([feats], np.array([0])).all(cfg.seq_len, cfg.max_gap)[0])  # same function the trainer batches with
    with torch.no_grad():
        probs = torch.softmax(rec.model(torch.from_numpy(x).unsqueeze(0)), dim=-1)[0].numpy()
    expected = {cfg.classes[i]: float(probs[i]) for i in range(len(cfg.classes))}
    got = {a["label"]: a["confidence"] for a in live["alternatives"]}
    assert set(got) == set(expected)
    for label, p in expected.items():
        assert got[label] == pytest.approx(p, abs=1e-6)
    assert live["label"] == max(expected, key=expected.get)


def test_below_threshold_is_unrecognized_and_sentence_unchanged(served, monkeypatch) -> None:
    monkeypatch.setattr(nlp_routes, "get_settings", lambda: Settings(model_dir=served, min_confidence=0.999))
    with client.websocket_connect("/ws/predict") as ws:
        ws.receive_json()
        ws.send_json({"type": "predict", "frames": frames()})
        r = ws.receive_json()
    assert r["accepted"] is False and r["label"] == "UNRECOGNIZED" and r["gloss"] is None and r["sequence"] == [] and r["english"] == ""
    assert r["confidence"] < 0.999 and len(r["alternatives"]) == 3  # the real scores are still shown


def test_accepted_signs_build_a_sentence_reset_clears_and_threshold_file_wins(served, tmp_path) -> None:
    with client.websocket_connect("/ws/predict") as ws:
        ws.receive_json()
        ws.send_json({"type": "predict", "frames": frames()})
        a = ws.receive_json()
        ws.send_json({"type": "predict", "frames": frames(20), "commit": False})
        b = ws.receive_json()
        ws.send_json({"type": "predict", "frames": frames(26)})
        c = ws.receive_json()
        ws.send_json({"type": "reset"})
        assert ws.receive_json() == {"type": "reset_ok"}
        ws.send_json({"type": "predict", "frames": frames(), "commit": False})
        d = ws.receive_json()
    assert a["accepted"] and len(a["sequence"]) == 1 and a["english"]
    assert b["sequence"] == a["sequence"]  # commit false does not extend the sentence
    assert len(c["sequence"]) == 2
    assert d["sequence"] == [] and d["english"] == ""
    (served / "threshold.json").write_text(json.dumps({"threshold": 0.9999}))
    try:
        with client.websocket_connect("/ws/predict") as ws:
            ready = ws.receive_json()
            assert ready["threshold"] == 0.9999 and ready["threshold_source"] == "validation"
    finally:
        (served / "threshold.json").unlink()


def test_bad_input_gets_an_error_and_the_connection_survives(served) -> None:
    with client.websocket_connect("/ws/predict") as ws:
        ws.receive_json()
        ws.send_text("not json")
        assert ws.receive_json()["error"] == "bad_message"
        ws.send_json({"type": "predict", "frames": []})
        assert ws.receive_json()["error"] == "bad_frames"
        ws.send_json({"type": "predict", "frames": [{"pose": None, "left_hand": None, "right_hand": None}] * 20})
        assert ws.receive_json()["error"] == "unusable_sequence"
        ws.send_json({"type": "predict", "frames": frames()})
        assert ws.receive_json()["type"] == "prediction"


# continuous mode -----------------------------------------------------------------------------------------------------------------------

def stream_frame(t: int, up: bool) -> dict:
    """Raw landmark frame: shoulders 0.2 apart at y 0.4; wrists up (y 0.5, moving) or down (y 0.95, still)."""
    f = frame()
    f["pose"] = [dict(p) for p in f["pose"]]
    y = 0.5 + 0.03 * np.sin(t / 2) if up else 0.95
    x = 0.3 + 0.05 * np.cos(t / 2) if up else 0.3
    f["pose"][15] = {"x": 0.7, "y": y, "z": 0.0}
    f["pose"][16] = {"x": x, "y": y, "z": 0.0}
    f["right_hand"] = [{"x": x, "y": y + 0.05, "z": 0.0}] * 21
    return f


def stream(pattern: list[tuple[bool, int]]) -> list[dict]:
    out, t = [], 0
    for up, n in pattern:
        for _ in range(n):
            out.append(stream_frame(t, up))
            t += 1
    return out


def collect(ws, until: str = "stream") -> list[dict]:
    got = []
    while True:
        m = ws.receive_json()
        got.append(m)
        if m["type"] == until:
            return got


def test_continuous_mode_finds_signs_builds_the_sentence_and_supports_undo_clear(served) -> None:
    with client.websocket_connect("/ws/predict") as ws:
        ws.receive_json()
        pattern = [(False, 10), (True, 22), (False, 12), (True, 26), (False, 12)]
        frames_all = stream(pattern)
        events = []
        for i in range(0, len(frames_all), 15):  # chunks, as the browser sends them
            ws.send_json({"type": "frames", "frames": frames_all[i : i + 15]})
            events += collect(ws)
        signs = [e for e in events if e["type"] == "sign"]
        assert len(signs) == 2
        assert all(e["accepted"] for e in signs)  # threshold 0.0 in this fixture: both are accepted
        assert signs[0]["segment"]["start"] < signs[0]["segment"]["end"] < signs[1]["segment"]["start"]
        last = [e for e in events if e["type"] == "stream"][-1]
        assert len(last["sequence"]) == 2 and last["english"] and last["frames_seen"] == len(frames_all)
        ws.send_json({"type": "undo"})
        u = ws.receive_json()
        assert u["type"] == "sequence" and u["removed"] == last["sequence"][-1] and u["sequence"] == last["sequence"][:1]
        ws.send_json({"type": "reset"})
        assert ws.receive_json() == {"type": "reset_ok"}
        ws.send_json({"type": "undo"})
        assert ws.receive_json()["removed"] is None  # nothing left to undo


def test_continuous_mode_unrecognized_segments_do_not_change_the_sentence_and_flush_closes_an_open_sign(served, monkeypatch) -> None:
    monkeypatch.setattr(nlp_routes, "get_settings", lambda: Settings(model_dir=served, min_confidence=0.999))
    with client.websocket_connect("/ws/predict") as ws:
        ws.receive_json()
        ws.send_json({"type": "frames", "frames": stream([(False, 8), (True, 24), (False, 10)])})
        ev = collect(ws)
        sign = [e for e in ev if e["type"] == "sign"][0]
        assert sign["accepted"] is False and sign["label"] == "UNRECOGNIZED" and ev[-1]["sequence"] == []
        ws.send_json({"type": "frames", "frames": stream([(False, 8), (True, 24)])})
        ev = collect(ws)
        assert [e for e in ev if e["type"] == "sign"] == [] and ev[-1]["active"] is True  # still signing
        ws.send_json({"type": "flush"})
        ev = collect(ws)
        assert [e["type"] for e in ev] == ["sign", "stream"] and ev[-1]["active"] is False


def test_continuous_mode_bad_chunks_get_errors_and_the_connection_survives(served) -> None:
    with client.websocket_connect("/ws/predict") as ws:
        ws.receive_json()
        ws.send_json({"type": "frames", "frames": []})
        assert ws.receive_json()["error"] == "bad_frames"
        ws.send_json({"type": "frames", "frames": [{"pose": "nope"}]})
        assert ws.receive_json()["error"] == "bad_frames"
        ws.send_json({"type": "frames", "frames": stream([(False, 5)])})
        m = collect(ws)
        assert m[-1]["type"] == "stream" and m[-1]["active"] is False and m[-1]["frames_seen"] == 5
