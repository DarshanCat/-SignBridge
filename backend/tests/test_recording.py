import json
import math

import numpy as np
from fastapi.testclient import TestClient

from app.avatar.clip import ClipFile
from app.core.config import Settings, get_settings
from app.main import app
from app.recognition.landmarks import FEATURE_DIM
from app.recording import MAX_NO_HAND_FRACTION, check_take, clean_gloss, frames_to_features
from app.schemas.landmarks import LandmarkFrame, Point

client = TestClient(app)


def teardown_function() -> None:
    app.dependency_overrides.clear()


def pose() -> list[dict]:
    pts = [{"x": 0.5, "y": 0.5, "z": 0.0} for _ in range(33)]
    pts[11] = {"x": 0.6, "y": 0.4, "z": 0.0}  # left shoulder
    pts[12] = {"x": 0.4, "y": 0.4, "z": 0.0}  # right shoulder
    pts[0] = {"x": 0.5, "y": 0.25, "z": 0.0}
    return pts


def hand(cx: float, cy: float) -> list[dict]:
    return [{"x": cx + 0.01 * (i % 5), "y": cy + 0.01 * (i // 5), "z": 0.0} for i in range(21)]


def frame(t: int, hands: bool = True, body: bool = True) -> dict:
    s = math.sin(t / 5)
    p = pose()
    p[16] = {"x": 0.3 + 0.05 * s, "y": 0.55 - 0.1 * abs(s), "z": 0.0}  # right wrist moves
    p[14] = {"x": 0.35, "y": 0.5, "z": 0.0}
    p[13] = {"x": 0.65, "y": 0.55, "z": 0.0}
    p[15] = {"x": 0.7, "y": 0.7, "z": 0.0}
    return {"pose": p if body else None, "left_hand": None, "right_hand": hand(0.3 + 0.05 * s, 0.5) if hands else None}


def take(n: int = 40, no_hand: int = 0, no_body: int = 0) -> list[dict]:
    return [frame(t, hands=t >= no_hand, body=not (no_hand <= t < no_hand + no_body)) for t in range(n)]


def post(tmp_path, frames, gloss="Test Sign", fps=30.0):
    app.dependency_overrides[get_settings] = lambda: Settings(record_dir=tmp_path / "rec")
    return client.post("/api/record/sign", json={"gloss": gloss, "fps": fps, "frames": frames})


def test_clean_gloss_normalizes_and_rejects_unsafe_names() -> None:
    assert clean_gloss(" good morning ") == "GOOD-MORNING"
    for bad in ["", "../x", "a/b", "-x", "A" * 40, "é"]:
        try:
            clean_gloss(bad)
        except ValueError:
            continue
        raise AssertionError(bad)


def test_features_use_the_225_format_and_check_counts_missing_hands() -> None:
    frames = [LandmarkFrame(**f) for f in take(30, no_hand=10)]
    feats, ok = frames_to_features(frames)
    assert feats.shape == (30, FEATURE_DIM) and ok.all()
    q = check_take(feats, ok, 30.0)
    assert q.stats.no_hand_frames == 10 and q.stats.frames == 30
    assert q.accepted == (10 / 30 <= MAX_NO_HAND_FRACTION)


def test_good_take_is_saved_as_features_and_an_unreviewed_self_recorded_clip(tmp_path) -> None:
    r = post(tmp_path, take(45))
    body = r.json()
    assert r.status_code == 200 and body["accepted"] and body["saved"], body
    clip = body["clip"]
    ClipFile.model_validate(clip)
    assert clip["source"]["review_status"] == "not_signer_reviewed" and clip["source"]["origin"] == "self-recorded"
    assert clip["source"]["source_sample"]["kind"] == "self-recorded"
    folder = tmp_path / "rec" / "TEST-SIGN"
    names = sorted(p.name for p in folder.iterdir())
    assert len(names) == 3 and any(n.endswith(".npy") for n in names) and any(n.endswith(".clip.json") for n in names)
    npy = next(folder.glob("*.npy"))
    assert np.load(npy).shape == (45, FEATURE_DIM)
    meta = json.loads(next(p for p in folder.glob("*.json") if not p.name.endswith(".clip.json")).read_text())
    assert meta["contains_video"] is False
    assert not any(p.suffix in {".mp4", ".webm", ".mov", ".avi"} for p in folder.iterdir())


def test_take_with_too_many_no_hand_frames_is_rejected_with_a_reason_and_not_stored(tmp_path) -> None:
    r = post(tmp_path, take(40, no_hand=25))
    body = r.json()
    assert not body["accepted"] and not body["saved"] and body["clip"] is None
    assert any("No hand was detected in 25 of 40" in m for m in body["reasons"])
    assert not (tmp_path / "rec").exists()


def test_lost_body_short_take_and_bad_fps_are_rejected(tmp_path) -> None:
    body = post(tmp_path, take(40, no_hand=5, no_body=15)).json()
    assert any("body was not detected" in m for m in body["reasons"])
    assert any("Only 10 frames" in m for m in post(tmp_path, take(10)).json()["reasons"])
    assert any("frame rate" in m for m in post(tmp_path, take(40), fps=2.0).json()["reasons"])


def test_bad_gloss_is_a_422_and_nothing_is_written(tmp_path) -> None:
    assert post(tmp_path, take(40), gloss="../evil").status_code == 422
    assert not (tmp_path / "rec").exists()


def test_two_takes_do_not_overwrite_each_other(tmp_path) -> None:
    post(tmp_path, take(40))
    post(tmp_path, take(41))
    assert len(list((tmp_path / "rec" / "TEST-SIGN").glob("*.npy"))) == 2
