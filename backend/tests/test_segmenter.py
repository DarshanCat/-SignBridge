import numpy as np
import pytest

from app.recognition.landmarks import FEATURE_DIM
from app.recognition.segmenter import LEFT_WRIST_X, LEFT_WRIST_Y, RIGHT_WRIST_X, RIGHT_WRIST_Y, SegmenterConfig, SignSegmenter


def row(wrist_y: float, wrist_x: float = 0.0) -> np.ndarray:
    r = np.zeros(FEATURE_DIM, dtype=np.float32)
    r[LEFT_WRIST_X], r[LEFT_WRIST_Y] = wrist_x, wrist_y
    r[RIGHT_WRIST_X], r[RIGHT_WRIST_Y] = -wrist_x, wrist_y
    return r


def rest(n: int) -> list[np.ndarray]:
    return [row(2.8) for _ in range(n)]


def sign(n: int, y: float = 0.5) -> list[np.ndarray]:
    return [row(y + 0.3 * np.sin(i / 2), 0.2 * np.cos(i / 2) * 2) for i in range(n)]  # raised and moving


def run(rows, cfg=None):
    seg = SignSegmenter(cfg)
    out = []
    for r in rows:
        out += seg.push(r)
    return seg, out


def test_one_sign_between_rest_is_found_with_padding() -> None:
    seg, out = run(rest(12) + sign(20) + rest(12))
    assert len(out) == 1
    s = out[0]
    assert (s.first_engaged, s.last_engaged) == (12, 31)
    assert s.start == 12 - 5 and s.end == 31 + 4 and len(s.features) == s.frames == 29
    assert not seg.active


def test_two_signs_separated_by_rest_and_a_sign_back_to_back_stays_one_segment() -> None:
    _, out = run(rest(8) + sign(15) + rest(10) + sign(18) + rest(8))
    assert [s.first_engaged for s in out] == [8, 33]
    _, merged = run(rest(8) + sign(15) + sign(18) + rest(8))
    assert len(merged) == 1  # no rest between them: documented limit


def test_short_wiggle_is_noise_and_a_still_raised_hand_counts_as_rest() -> None:
    _, out = run(rest(10) + sign(4) + rest(10))
    assert out == []  # fewer than min_engaged engaged frames
    held = [row(0.5, 0.1)] * 30  # raised but not moving
    _, out = run(rest(8) + sign(15) + held + rest(5))
    assert len(out) == 1 and out[0].last_engaged < 8 + 15 + 12  # the hold ended the sign after still_frames


def test_open_sign_is_closed_by_flush_and_long_sign_is_cut_at_max_frames() -> None:
    seg, out = run(rest(8) + sign(20))
    assert out == [] and seg.active
    flushed = seg.flush()
    assert len(flushed) == 1 and not seg.active
    _, out = run(rest(5) + sign(300), SegmenterConfig(max_frames=60))
    assert out and all(s.frames <= 60 + 5 + 4 for s in out)


def test_reset_clears_everything() -> None:
    seg, _ = run(rest(5) + sign(10))
    seg.reset()
    assert seg.index == -1 and not seg.active and seg.flush() == []


def test_config_can_be_overridden() -> None:
    _, out = run(rest(8) + sign(20, y=1.8) + rest(8), SegmenterConfig(rest_y=1.0))
    assert out == []  # the wrists never get above the stricter rest line
