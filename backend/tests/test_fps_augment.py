"""Frame rate augmentation: thinning to a camera rate, off by default, same random stream when off, reproducible when on."""

import numpy as np
import pytest

from app.recognition.landmarks import FEATURE_DIM
from training.augment import BASE_FPS, fps_augment, thin_to_rate
from training.dataset import SequenceStore


def seq(t=32, width=4):
    return np.arange(t * width, dtype=np.float32).reshape(t, width)


def test_a_rate_at_or_above_the_base_rate_changes_nothing() -> None:
    s = seq()
    assert thin_to_rate(s, 12.5) is s and thin_to_rate(s, 25.0) is s
    assert BASE_FPS == 12.5


def test_thinning_picks_the_frames_nearest_to_the_camera_times() -> None:
    s = seq(30, 1)
    # 6.25 fps from 12.5 fps keeps every second frame: times 0, 0.16, 0.32 s are frames 0, 2, 4
    assert thin_to_rate(s, 6.25)[:, 0].tolist() == [float(i) for i in range(0, 30, 2)]
    # 6.7 fps: step 12.5 / 6.7 = 1.866 frames
    got = thin_to_rate(s, 6.7)[:, 0]
    assert got[0] == 0 and np.all(np.diff(got) >= 1) and np.all(np.diff(got) <= 2) and len(got) == 16
    # a phase moves the first kept frame by a fraction of a step
    assert thin_to_rate(s, 6.25, phase=0.5)[0, 0] == 1.0
    # a very short sequence still keeps two frames (the first and the last)
    assert thin_to_rate(seq(3, 1), 6.0)[:, 0].tolist() == [0.0, 2.0]
    assert thin_to_rate(seq(2, 1), 6.0)[:, 0].tolist() == [0.0, 1.0]  # fewer than two frames would be left: the first and the last are kept


def test_it_works_for_any_width() -> None:
    assert thin_to_rate(seq(20, 375), 8.0).shape[1] == 375


def test_fps_augment_draws_a_rate_in_the_range_and_is_reproducible() -> None:
    s = seq(40, 3)
    lens = [len(fps_augment(s, np.random.default_rng(k))) for k in range(300)]
    assert min(lens) >= 40 * 6.0 / 12.5 - 2 and max(lens) <= 40  # between 6 and 12.5 fps
    assert len(set(lens)) > 5  # different rates are drawn
    assert np.array_equal(fps_augment(s, np.random.default_rng(3)), fps_augment(s, np.random.default_rng(3)))
    assert np.mean(lens) == pytest.approx(40 * (6 + 12.5) / 2 / 12.5, abs=2.0)  # the mean rate is the middle of the range


def test_batches_are_unchanged_and_draw_nothing_when_it_is_off() -> None:
    rng0 = np.random.default_rng(5)
    store = SequenceStore([np.random.default_rng(1).random((25, FEATURE_DIM)).astype(np.float32) for _ in range(4)], np.arange(4))
    a = store.batch(np.arange(4), 32, 3, rng0)  # no augmentation configured: as before
    b = store.batch(np.arange(4), 32, 3, np.random.default_rng(5), None, None, None)
    assert np.array_equal(a, b)
    assert rng0.random() == np.random.default_rng(5).random()  # the generator was not used
    c = store.batch(np.arange(4), 32, 3, np.random.default_rng(5), None, None, (6.0, 12.5))
    assert c.shape == a.shape and not np.array_equal(c, a)  # thinned sequences resampled to 32 frames differ from the originals
    assert np.array_equal(store.all(32, 3), store.batch(np.arange(4), 32, 3))  # evaluation never thins
