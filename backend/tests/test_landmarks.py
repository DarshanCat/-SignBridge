import numpy as np
from fastapi.testclient import TestClient

from app.main import app
from app.recognition.landmarks import FEATURE_DIM, MIN_HAND_FRAMES, MIN_VALID_FRAMES, normalize_frame
from app.schemas.landmarks import LandmarkFrame, Point

client = TestClient(app)


def pt(x: float, y: float, z: float = 0.0) -> dict:
    return {"x": x, "y": y, "z": z}


def pose(cx: float = 0.5, width: float = 0.2) -> list[dict]:
    pts = [pt(cx, 0.5)] * 33
    pts = list(pts)
    pts[11] = pt(cx - width / 2, 0.4)
    pts[12] = pt(cx + width / 2, 0.4)
    return pts


def hand(x: float = 0.3) -> list[dict]:
    return [pt(x, 0.6)] * 21


def frame(**kw) -> dict:
    return {"pose": pose(), "left_hand": hand(), "right_hand": None, **kw}


def test_feature_dim_and_hand_zero_fill() -> None:
    feats, rep = normalize_frame(LandmarkFrame.model_validate(frame()))
    assert feats.shape == (FEATURE_DIM,)
    assert rep.valid and rep.has_left_hand and not rep.has_right_hand
    assert not feats[(33 + 21) * 3 :].any()


def test_normalization_is_translation_and_scale_invariant() -> None:
    a, _ = normalize_frame(LandmarkFrame.model_validate({"pose": pose(0.5, 0.2), "left_hand": hand(0.3)}))
    b_pose = [pt(p["x"] * 2 + 0.1, p["y"] * 2 + 0.1) for p in pose(0.5, 0.2)]
    b_hand = [pt(p["x"] * 2 + 0.1, p["y"] * 2 + 0.1) for p in hand(0.3)]
    b, _ = normalize_frame(LandmarkFrame.model_validate({"pose": b_pose, "left_hand": b_hand}))
    assert np.allclose(a, b, atol=1e-5)


def test_missing_pose_invalid() -> None:
    feats, rep = normalize_frame(LandmarkFrame.model_validate({"left_hand": hand()}))
    assert not rep.valid and "pose: missing" in rep.issues and not feats.any()


def test_wrong_landmark_count_invalid() -> None:
    _, rep = normalize_frame(LandmarkFrame.model_validate({"pose": pose()[:10]}))
    assert not rep.valid


def test_degenerate_shoulders_invalid() -> None:
    _, rep = normalize_frame(LandmarkFrame.model_validate({"pose": pose(width=0.0)}))
    assert not rep.valid


def test_nan_hand_dropped_but_frame_valid() -> None:
    bad = [Point(x=float("nan"), y=0, z=0)] * 21
    _, rep = normalize_frame(LandmarkFrame(pose=[Point(**p) for p in pose()], left_hand=bad))
    assert rep.valid and not rep.has_left_hand and rep.issues


def test_endpoint_usable_sequence() -> None:
    n = max(MIN_VALID_FRAMES, MIN_HAND_FRAMES)
    r = client.post("/api/landmarks/extract", json={"frames": [frame()] * n})
    body = r.json()
    assert r.status_code == 200 and body["usable"] and body["feature_dim"] == FEATURE_DIM
    assert len(body["features"]) == n


def test_endpoint_too_few_frames_not_usable() -> None:
    body = client.post("/api/landmarks/extract", json={"frames": [frame()]}).json()
    assert not body["usable"] and body["warnings"]


def test_endpoint_rejects_empty_and_oversized() -> None:
    assert client.post("/api/landmarks/extract", json={"frames": []}).status_code == 422
    assert client.post("/api/landmarks/extract", json={"frames": [{}] * 301}).status_code == 422
    assert client.post("/api/landmarks/extract", json={"frames": [{"pose": "x"}]}).status_code == 422


def test_vectorized_resample_matches_np_interp():
    import numpy as np

    from app.recognition.landmarks import FEATURE_DIM
    from app.recognition.preprocess import resample_sequence

    rng = np.random.default_rng(0)
    for t, length in [(2, 32), (7, 32), (32, 32), (33, 32), (90, 32), (300, 32), (50, 13), (5, 100)]:
        x = rng.normal(size=(t, FEATURE_DIM)).astype(np.float32)
        src, dst = np.linspace(0.0, 1.0, t), np.linspace(0.0, 1.0, length)
        want = np.stack([np.interp(dst, src, x[:, i]) for i in range(FEATURE_DIM)], axis=1).astype(np.float32)
        got = resample_sequence(x, length)
        if t == length:
            np.testing.assert_array_equal(got, x)
        np.testing.assert_allclose(got, want, atol=1e-6)
    one = rng.normal(size=(1, FEATURE_DIM)).astype(np.float32)
    assert resample_sequence(one, 5).shape == (5, FEATURE_DIM)
