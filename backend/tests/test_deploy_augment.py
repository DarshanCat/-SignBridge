"""Deployment augmentation: the y scale must equal what re-normalizing scaled raw landmarks gives, and the other two must keep missing data missing."""

import numpy as np

from app.recognition.landmarks import FEATURE_DIM, normalize_frame
from app.schemas.landmarks import LandmarkFrame, Point
from training.augment import DeployAugmentConfig, deploy_augment, drop_hands, landmark_noise, y_scale_features


def raw_frame(rng, hands=True, tilt=0.03):
    pose = [Point(x=float(rng.uniform(0.2, 0.8)), y=float(rng.uniform(0.1, 0.9)), z=float(rng.normal(0, 0.1))) for _ in range(33)]
    pose[11] = Point(x=0.45, y=0.40 + tilt, z=0.0)  # slightly tilted shoulders, so the hypot matters
    pose[12] = Point(x=0.58, y=0.40, z=0.0)
    hand = lambda: [Point(x=float(rng.uniform(0.2, 0.8)), y=float(rng.uniform(0.2, 0.9)), z=float(rng.normal(0, 0.05))) for _ in range(21)]  # noqa: E731
    return LandmarkFrame(pose=pose, left_hand=hand() if hands else None, right_hand=hand())


def scaled(frame: LandmarkFrame, s: float) -> LandmarkFrame:
    f = lambda pts: None if pts is None else [Point(x=p.x, y=p.y * s, z=p.z) for p in pts]  # noqa: E731
    return LandmarkFrame(pose=f(frame.pose), left_hand=f(frame.left_hand), right_hand=f(frame.right_hand))


def test_y_scale_equals_renormalizing_scaled_raw_landmarks():
    rng = np.random.default_rng(0)
    frames = [raw_frame(rng, hands=i % 2 == 0) for i in range(6)]
    base = np.stack([normalize_frame(f)[0] for f in frames])
    for s in (0.85, 1.0, 1.2, 1.333):
        expect = np.stack([normalize_frame(scaled(f, s))[0] for f in frames])
        np.testing.assert_allclose(y_scale_features(base, s), expect, atol=1e-5)


def test_y_scale_keeps_zero_rows_and_missing_hands_zero():
    rng = np.random.default_rng(1)
    base = np.stack([normalize_frame(raw_frame(rng, hands=False))[0], np.zeros(FEATURE_DIM, dtype=np.float32)])
    out = y_scale_features(base, 1.2)
    assert not out[1].any()
    assert not out[0, 99:162].any()  # left hand was missing


def test_noise_never_touches_missing_points():
    x = np.zeros((10, FEATURE_DIM), dtype=np.float32)
    x[:, :99] = 1.0
    out = landmark_noise(x, np.random.default_rng(0), 0.05)
    assert not out[:, 99:].any()
    assert np.abs(out[:, :99:3] - 1.0).max() > 0  # x moved
    np.testing.assert_array_equal(out[:, 2:99:3], 1.0)  # z untouched


def test_hand_dropout_rate_and_pose_untouched():
    x = np.ones((4000, FEATURE_DIM), dtype=np.float32)
    out = drop_hands(x, np.random.default_rng(0), 0.2)
    left_gone = float((out[:, 99:162].sum(axis=1) == 0).mean())
    assert 0.17 < left_gone < 0.23
    assert (out[:, :99] == 1.0).all()
    assert (drop_hands(x, np.random.default_rng(0), 0.0) == 1.0).all()


def test_deploy_augment_is_reproducible_and_changes_the_input():
    rng = np.random.default_rng(2)
    x = np.stack([normalize_frame(raw_frame(rng))[0] for _ in range(20)])
    a = deploy_augment(x, np.random.default_rng(5), DeployAugmentConfig())
    b = deploy_augment(x, np.random.default_rng(5), DeployAugmentConfig())
    np.testing.assert_array_equal(a, b)
    assert a.shape == x.shape and a.dtype == np.float32
    assert np.abs(a - x).max() > 0
