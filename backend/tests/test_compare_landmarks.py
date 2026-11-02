import json

import numpy as np
import pytest

from app.schemas.landmarks import LandmarkFrame
from tests.test_landmarks import frame
from training.compare_landmarks import (
    CompareError,
    compare_features,
    load_browser,
    pair_by_time,
    to_features,
    verdict,
)


def frames(n=10, shift=0.0, hands=True, body=True):
    out = []
    for t in range(n):
        f = frame()
        f["pose"] = [dict(p) for p in f["pose"]]
        f["pose"][16] = {"x": 0.3 + 0.01 * t + shift, "y": 0.5, "z": 0.0}
        f["right_hand"] = [{"x": 0.3 + 0.01 * t + shift, "y": 0.55, "z": 0.0}] * 21 if hands else None
        f["left_hand"] = None
        if not body:
            f["pose"] = None
        out.append(LandmarkFrame(**f))
    return out


def test_pairing_by_time_uses_each_frame_once_and_respects_the_tolerance() -> None:
    a = np.array([0.0, 40.0, 80.0, 120.0])
    b = np.array([5.0, 45.0, 400.0])
    assert pair_by_time(a, b, 20.0) == [(0, 0), (1, 1)]
    assert pair_by_time(a, a, 1.0) == [(0, 0), (1, 1), (2, 2), (3, 3)]


def test_identical_landmarks_have_zero_distance_and_full_agreement() -> None:
    fb, ok = to_features(frames())
    r = compare_features(fb, ok, fb.copy(), ok.copy(), [(i, i) for i in range(10)])
    d = r["distance_in_shoulder_widths"]
    assert d["pose_33_points"]["median"] == 0 and d["right_hand"]["median"] == 0 and d["left_hand"] is None
    assert r["detection_agreement"]["pose"]["both"] == 10 and r["detection_agreement"]["right_hand"]["both"] == 10
    assert r["detection_agreement"]["left_hand"]["neither"] == 10


def test_a_known_shift_is_reported_in_shoulder_widths() -> None:
    # the shoulders are 0.2 apart, so moving the right wrist and hand by 0.05 is 0.25 shoulder widths for those landmarks
    fb, ok = to_features(frames())
    fp, okp = to_features(frames(shift=0.05))
    r = compare_features(fb, ok, fp, okp, [(i, i) for i in range(10)])
    assert r["distance_in_shoulder_widths"]["right_hand"]["median"] == pytest.approx(0.25, abs=1e-4)
    arms = r["distance_in_shoulder_widths"]["arms_shoulder_to_wrist"]["median"]
    assert arms == pytest.approx(0.25 / 6, abs=1e-4)  # one of six arm landmarks (the wrist) moved


def test_detection_disagreement_is_counted() -> None:
    fb, ok = to_features(frames())
    fp, okp = to_features(frames(hands=False))
    r = compare_features(fb, ok, fp, okp, [(i, i) for i in range(10)])
    assert r["detection_agreement"]["right_hand"] == {"both": 0, "browser_only": 10, "python_only": 0, "neither": 0}
    fb2, ok2 = to_features(frames(body=False))
    r2 = compare_features(fb2, ok2, fp, okp, [(i, i) for i in range(10)])
    assert r2["detection_agreement"]["pose"]["python_only"] == 10
    assert "could not be compared" in verdict(r2)


def test_verdict_text_gives_scale() -> None:
    fb, ok = to_features(frames())
    fp, okp = to_features(frames(shift=0.05))
    text = verdict(compare_features(fb, ok, fp, okp, [(i, i) for i in range(10)]))
    assert "shoulder widths" in text and "right hand median 0.250" in text


def test_browser_file_loading_and_errors(tmp_path) -> None:
    good = tmp_path / "t.landmarks.json"
    good.write_text(json.dumps({"version": 1, "video_duration_ms": 1000, "frames": [{"t": 0, "pose": None, "left_hand": None, "right_hand": None}, {"t": 50, "pose": None, "left_hand": None, "right_hand": None}]}))
    fr, t, meta = load_browser(good)
    assert len(fr) == 2 and list(t) == [0, 50] and meta["video_duration_ms"] == 1000
    for bad in ["not json", json.dumps({"frames": []}), json.dumps({"nope": 1})]:
        p = tmp_path / "bad.json"
        p.write_text(bad)
        with pytest.raises(CompareError):
            load_browser(p)
