"""add_source_landmarks on synthetic features: the stored block has the documented shape and the clip's motion tracks are never touched."""

import numpy as np
import pytest

from app.recognition.landmarks import HAND_POINTS, POSE_POINTS
from retarget.add_source_landmarks import LEFT_END, POSE_END, POSE_KEEP, VERSION, keyframe_times, landmarks_block

FRAME = LEFT_END + HAND_POINTS * 3


def seq(frames=4):
    rng = np.random.default_rng(1)
    s = rng.random((frames, FRAME)).astype(np.float32)
    s[1, POSE_END:LEFT_END] = 0  # left hand not detected in frame 1
    return s


def test_block_shape_and_missing_hand_is_none():
    s = seq()
    b = landmarks_block(s, [0.1, 0.2, 0.3, 0.4])
    assert b["version"] == VERSION and b["pose_idx"] == POSE_KEEP
    assert len(b["pose"]) == 4 and len(b["pose"][0]) == len(POSE_KEEP)
    assert b["left"][1] is None and len(b["left"][0]) == HAND_POINTS and len(b["right"][3]) == HAND_POINTS
    assert b["pose"][2][POSE_KEEP.index(16)] == [round(float(v), 3) for v in s[2, 16 * 3 : 16 * 3 + 3]]
    assert POSE_END == POSE_POINTS * 3


def test_keyframe_times_skip_the_rest_ramps_and_must_match_the_frame_count():
    clip = {"tracks": [{"keyframes": [{"t": 0}, {"t": 0.5}, {"t": 0.9}, {"t": 1.4}]}, {"keyframes": [{"t": 0}, {"t": 1.4}]}]}
    assert keyframe_times(clip, 2) == [0.5, 0.9]
    with pytest.raises(ValueError):
        keyframe_times(clip, 3)
