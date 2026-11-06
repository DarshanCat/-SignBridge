"""Mirror augmentation for left-handed signers: an exact mirror image about the shoulder midpoint with left and right swapped."""

import numpy as np
import pytest

from app.recognition.landmarks import FEATURE_DIM, HAND_POINTS, POSE_POINTS
from app.recognition.preprocess import LEFT_END, POSE_END, hand_missing_mask
from training.augment import AugmentConfig, POSE_MIRROR_PAIRS, augment_sequence, mirror_features


def sample(t=12, left=True, right=True, seed=0):
    x = np.random.default_rng(seed).normal(size=(t, FEATURE_DIM)).astype(np.float32)
    if not left:
        x[:, POSE_END:LEFT_END] = 0
    if not right:
        x[:, LEFT_END:] = 0
    return x


def test_mirroring_twice_gives_the_input_back() -> None:
    x = sample()
    assert np.allclose(mirror_features(mirror_features(x)), x)


def test_x_is_negated_sides_swap_y_and_z_are_kept() -> None:
    x = sample()
    m = mirror_features(x)
    p, q = x[:, :POSE_END].reshape(-1, POSE_POINTS, 3), m[:, :POSE_END].reshape(-1, POSE_POINTS, 3)
    assert np.allclose(q[:, 0], p[:, 0] * [-1, 1, 1])  # the nose stays on the middle line
    for a, b in POSE_MIRROR_PAIRS:  # shoulders 11 and 12, wrists 15 and 16, ...
        assert np.allclose(q[:, a], p[:, b] * [-1, 1, 1]) and np.allclose(q[:, b], p[:, a] * [-1, 1, 1])
    right = x[:, LEFT_END:].reshape(-1, HAND_POINTS, 3)
    new_left = m[:, POSE_END:LEFT_END].reshape(-1, HAND_POINTS, 3)
    assert np.allclose(new_left, right * [-1, 1, 1])  # the mirrored right hand is the new left hand, same landmark order
    # independent of the list under test: the MediaPipe pose layout (nose 0, left eye 1-3, right eye 4-6, ears 7-8, mouth 9-10, shoulders 11-12, ...)
    assert len(POSE_MIRROR_PAIRS) == 16 and sorted(i for pr in POSE_MIRROR_PAIRS for i in pr) == list(range(1, 33))
    assert {frozenset(pr) for pr in POSE_MIRROR_PAIRS} >= {frozenset({1, 4}), frozenset({2, 5}), frozenset({3, 6}), frozenset({7, 8}),
                                                         frozenset({9, 10}), frozenset({11, 12}), frozenset({15, 16}), frozenset({23, 24})}
    from app.recognition.landmarks import LEFT_SHOULDER, RIGHT_SHOULDER

    assert (LEFT_SHOULDER, RIGHT_SHOULDER) == (11, 12)


def test_a_right_handed_sign_becomes_the_left_handed_sign() -> None:
    x = sample(left=False)  # only the right hand signs
    m = mirror_features(x)
    left_missing, right_missing = hand_missing_mask(m)
    assert right_missing.all() and not left_missing.any()  # now only the left hand
    assert not m[:, LEFT_END:].any() and not np.isnan(m).any()
    assert not (np.signbit(m[:, LEFT_END:]) & (m[:, LEFT_END:] == 0)).any()  # zeros are plain zeros, not -0.0 (a missing hand stays missing)


def test_wrong_shape_is_refused() -> None:
    with pytest.raises(ValueError):
        mirror_features(np.zeros((5, 10), np.float32))


def test_augment_mirrors_with_the_given_probability_and_is_off_by_default() -> None:
    assert AugmentConfig().p_mirror == 0.0
    x = sample(t=20)
    cfg_off = AugmentConfig(p_speed=0, p_jitter=0, p_rotate=0, p_scale=0)
    assert np.allclose(augment_sequence(x, np.random.default_rng(1), cfg_off), x)  # nothing drawn, nothing changed
    cfg_on = AugmentConfig(p_speed=0, p_jitter=0, p_rotate=0, p_scale=0, p_mirror=1.0)
    assert np.allclose(augment_sequence(x, np.random.default_rng(1), cfg_on), mirror_features(x))
    flips = sum(not np.allclose(augment_sequence(x, np.random.default_rng(s), AugmentConfig(p_speed=0, p_jitter=0, p_rotate=0, p_scale=0, p_mirror=0.5)), x) for s in range(200))
    assert 70 < flips < 130  # about half


def test_the_random_stream_of_earlier_runs_is_unchanged_when_mirroring_is_off() -> None:
    x = sample(t=24)
    a = augment_sequence(x, np.random.default_rng(7))
    b = augment_sequence(x, np.random.default_rng(7), AugmentConfig(p_mirror=0.0))
    assert np.array_equal(a, b)
