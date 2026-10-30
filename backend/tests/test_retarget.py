"""Retarget tests on synthetic landmarks. Forward kinematics (the same three.js conventions the avatar uses) checks that the
recovered rotations put the rig's bones where the landmarks were. They say nothing about whether a retargeted clip looks like a correct sign."""

import json

import numpy as np
import pytest

from app.avatar.clip import BONES, ClipFile
from retarget.clip_builder import build_clip, sequence_to_tracks
from retarget.geometry import (
    REST_DIR, euler_to_matrix, frame_rotation, landmarks_to_rig, matrix_to_euler, rotation_between, unit,
)
from retarget.make_clip import main as make_clip_main
from retarget.pose_to_rig import FINGERS, finger_curl, frame_to_bones

LEFT_START, RIGHT_START = 99, 162
RIG = np.random.default_rng(3)


def to_mp(p: np.ndarray) -> np.ndarray:
    return landmarks_to_rig(p)  # the conversion is its own inverse


def set_pose(x: np.ndarray, idx: int, p: np.ndarray) -> None:
    x[idx * 3 : idx * 3 + 3] = to_mp(p)


def frame(left_arm, right_arm, left_hand=None, right_hand=None) -> np.ndarray:
    """left_arm and right_arm are (shoulder, elbow, wrist) in RIG coordinates; hands are (21, 3) rig coordinates or None."""
    x = np.zeros(225)
    for (sh, el, wr), (i_sh, i_el, i_wr) in ((left_arm, (11, 13, 15)), (right_arm, (12, 14, 16))):
        set_pose(x, i_sh, sh), set_pose(x, i_el, el), set_pose(x, i_wr, wr)
    for start, hand in ((LEFT_START, left_hand), (RIGHT_START, right_hand)):
        if hand is not None:
            x[start : start + 63] = to_mp(hand).reshape(-1)
    return x


def arm(side: float, upper=(0.0, -1.0, 0.0), fore=(0.0, -1.0, 0.0)):
    sh = np.array([0.5 * side, 0.0, 0.0])
    el = sh + 0.6 * unit(np.array(upper))
    return sh, el, el + 0.55 * unit(np.array(fore))


def straight_hand(wrist: np.ndarray, fwd: np.ndarray, side_vec: np.ndarray) -> np.ndarray:
    """A flat hand: knuckles along `side_vec` (index to pinky), fingers along `fwd`."""
    f, u = unit(fwd), unit(side_vec)
    pts = np.zeros((21, 3))
    pts[0] = wrist
    for chain, off in zip(FINGERS.values(), (-1.5, -0.5, 0.0, 0.5, 1.5)):
        base = wrist + 0.09 * f + 0.02 * off * (-u) * -1
        for k, idx in enumerate(chain[1:]):
            pts[idx] = base + 0.03 * k * f
    pts[5] = wrist + 0.09 * f - 0.02 * u * 1.5  # index knuckle
    pts[17] = wrist + 0.08 * f + 0.02 * u * 1.5  # pinky knuckle
    pts[9] = wrist + 0.1 * f
    return pts


def euler_bones(bones, name):
    return euler_to_matrix(bones[name])


# geometry ---------------------------------------------------------------------------------------------------------------

def test_euler_matrix_round_trip_and_three_js_order() -> None:
    for _ in range(50):
        e = tuple(RIG.uniform(-1.4, 1.4, 3))
        assert np.allclose(matrix_to_euler(euler_to_matrix(e)), e, atol=1e-9)
    # three.js XYZ: rotating by x then applying y is Rx @ Ry (a pure x rotation moves -y toward -z when positive)
    assert np.allclose(euler_to_matrix((np.pi / 2, 0, 0)) @ REST_DIR, [0, 0, -1], atol=1e-12)
    assert np.allclose(euler_to_matrix((-np.pi / 2, 0, 0)) @ REST_DIR, [0, 0, 1], atol=1e-12)  # negative x raises the arm toward the camera


def test_rotation_between_includes_antiparallel_and_identical() -> None:
    for _ in range(50):
        a, b = unit(RIG.normal(size=3)), unit(RIG.normal(size=3))
        assert np.allclose(rotation_between(a, b) @ a, b, atol=1e-9)
    assert np.allclose(rotation_between(REST_DIR, REST_DIR), np.eye(3))
    r = rotation_between(REST_DIR, -REST_DIR)
    assert np.allclose(r @ REST_DIR, -REST_DIR) and np.allclose(r @ r.T, np.eye(3), atol=1e-9)


def test_frame_rotation_maps_forward_and_side_vectors() -> None:
    f0, u0 = np.array([0, -1.0, 0]), np.array([-1.0, 0, 0])
    f1, u1 = unit(np.array([0.2, 0.9, 0.4])), unit(np.array([0.7, -0.1, 0.5]))
    r = frame_rotation(f0, u0, f1, u1)
    assert np.allclose(r @ f0, f1, atol=1e-9) and np.allclose(np.linalg.det(r), 1)
    u_ortho = unit(u1 - np.dot(u1, f1) * f1)
    assert np.allclose(r @ u0, u_ortho, atol=1e-9)


# arms and hands: forward kinematics must reproduce the landmark directions --------------------------------------------------

@pytest.mark.parametrize("side, key", [(1.0, "l"), (-1.0, "r")])
def test_arm_chain_forward_kinematics_matches_landmarks(side, key) -> None:
    for _ in range(25):
        upper = unit(RIG.normal(size=3) * [1, 1, 1] + [0, -0.5, 0.3])
        fore = unit(RIG.normal(size=3))
        l_arm, r_arm = (arm(side, upper, fore), arm(-side)) if side > 0 else (arm(-side), arm(side, upper, fore))
        bones, _ = frame_to_bones(frame(l_arm, r_arm))
        w_upper = euler_to_matrix(bones[f"upperArm_{key}"])
        w_fore = w_upper @ euler_to_matrix(bones[f"foreArm_{key}"])
        assert np.allclose(w_upper @ REST_DIR, upper, atol=1e-7)
        assert np.allclose(w_fore @ REST_DIR, fore, atol=1e-7)


def test_rest_arms_give_zero_rotation_and_missing_hands_stay_at_rest() -> None:
    bones, present = frame_to_bones(frame(arm(1.0), arm(-1.0)))
    assert present == {"l": False, "r": False}
    assert all(np.allclose(v, 0, atol=1e-9) for v in bones.values())


def test_raised_forward_arm_matches_the_avatar_convention() -> None:
    bones, _ = frame_to_bones(frame(arm(1.0, upper=(0, 0, 1.0)), arm(-1.0)))
    assert bones["upperArm_l"][0] == pytest.approx(-np.pi / 2, abs=1e-9)  # negative x rotation raises the arm toward the camera


def test_hand_orientation_forward_kinematics() -> None:
    l_arm, r_arm = arm(1.0, upper=(0.3, -0.5, 0.8), fore=(0.1, 0.9, 0.3)), arm(-1.0)
    wrist = l_arm[2]
    fwd, side_vec = unit(np.array([0.2, 0.8, 0.5])), unit(np.array([-0.9, 0.2, 0.3]))
    hand = straight_hand(wrist, fwd, side_vec)
    bones, present = frame_to_bones(frame(l_arm, r_arm, left_hand=hand))
    assert present["l"] and not present["r"]
    w = euler_to_matrix(bones["upperArm_l"]) @ euler_to_matrix(bones["foreArm_l"]) @ euler_to_matrix(bones["hand_l"])
    f_target = unit(hand[9] - hand[0])
    side_target = hand[17] - hand[5]
    assert np.allclose(w @ REST_DIR, f_target, atol=1e-7)
    assert np.allclose(w @ np.array([-1.0, 0, 0]), unit(side_target - np.dot(side_target, f_target) * f_target), atol=1e-7)


def test_finger_curl_values_and_clamp() -> None:
    pts = np.zeros((21, 3))
    chain = FINGERS["index"]
    for i, idx in enumerate(chain):
        pts[idx] = [0, 0.03 * i, 0]  # straight line
    assert finger_curl(pts, chain) == pytest.approx(0.0, abs=1e-9)
    pts2 = pts.copy()
    pts2[8] = pts2[7] + [0.03, 0, 0]  # last segment bent by 90 degrees
    assert finger_curl(pts2, chain) == pytest.approx(np.pi / 2, abs=1e-9)
    hand = straight_hand(np.zeros(3), np.array([0, 1.0, 0]), np.array([-1.0, 0, 0]))
    for name, ch in FINGERS.items():  # fully curled finger: every joint bends 90 degrees, total above the clamp
        hand[ch[1]] = hand[0] + [0.03, 0, 0]
    bones, _ = frame_to_bones(frame(arm(1.0), arm(-1.0), left_hand=hand))
    assert all(bones[f"hand_l.{n}"][0] <= 0 and bones[f"hand_l.{n}"][0] >= -2.4 - 1e-9 for n in FINGERS)


def test_mirror_symmetry_of_conventions() -> None:
    l_arm, r_arm = arm(1.0, upper=(0.3, -0.5, 0.8), fore=(0.1, 0.9, 0.3)), arm(-1.0, upper=(-0.2, -0.6, 0.5), fore=(0.4, -0.2, 0.7))
    left_hand = straight_hand(l_arm[2], np.array([0.2, 0.8, 0.5]), np.array([-0.9, 0.2, 0.3]))
    right_hand = straight_hand(r_arm[2], np.array([-0.3, 0.7, 0.4]), np.array([0.8, 0.3, 0.2]))
    a, _ = frame_to_bones(frame(l_arm, r_arm, left_hand, right_hand))
    mir = lambda p: p * np.array([-1.0, 1.0, 1.0])  # noqa: E731  reflect across the x = 0 plane
    b, _ = frame_to_bones(frame(
        tuple(mir(p) for p in r_arm), tuple(mir(p) for p in l_arm), mir(right_hand), mir(left_hand),
    ))
    for name in ("upperArm", "foreArm", "hand"):
        ea, eb = a[f"{name}_l"], b[f"{name}_r"]
        assert np.allclose(ea, (eb[0], -eb[1], -eb[2]), atol=1e-6), name
    for f in FINGERS:
        assert a[f"hand_l.{f}"][0] == pytest.approx(b[f"hand_r.{f}"][0], abs=1e-9)


def test_bad_inputs() -> None:
    with pytest.raises(ValueError):
        frame_to_bones(np.zeros(10))
    with pytest.raises(ValueError, match="degenerate"):
        frame_to_bones(np.zeros(225))
    with pytest.raises(ValueError):
        sequence_to_tracks(np.zeros((1, 225)))


# clip builder -------------------------------------------------------------------------------------------------------------

def moving_sequence(n: int = 20, with_hand: bool = True) -> np.ndarray:
    frames = []
    for i in range(n):
        ang = 0.8 * np.sin(np.pi * i / (n - 1))
        upper = (0.0, -np.cos(ang), np.sin(ang))
        l_arm = arm(1.0, upper=upper, fore=(0, -1, 0.2 + 0.3 * np.sin(ang)))
        hand = straight_hand(l_arm[2], np.array([0, 1.0, 0.2]), np.array([-1.0, 0, 0])) if with_hand else None
        frames.append(frame(l_arm, arm(-1.0), left_hand=hand))
    return np.stack(frames)


def make(seq, **kw):
    return build_clip(seq, "hello", fps=30, stride=2, author="test", license_text="test", description="synthetic", **kw)


def test_clip_is_valid_starts_and_ends_at_rest_and_has_the_expected_duration() -> None:
    clip = make(moving_sequence(20))
    ClipFile.model_validate(clip)
    assert clip["gloss"] == "HELLO"
    assert clip["duration"] == pytest.approx(19 * 2 / 30 + 0.5, abs=1e-3)
    assert clip["tracks"] and all(t["bone"] in BONES for t in clip["tracks"])
    for t in clip["tracks"]:
        assert t["keyframes"][0]["rot"] == [0.0, 0.0, 0.0] and t["keyframes"][-1]["rot"] == [0.0, 0.0, 0.0]
        times = [k["t"] for k in t["keyframes"]]
        assert times == sorted(times) and times[-1] == clip["duration"]
    assert "upperArm_l" in {t["bone"] for t in clip["tracks"]} and "upperArm_r" not in {t["bone"] for t in clip["tracks"]}
    json.dumps(clip)


def test_missing_hand_is_held_then_relaxed_not_invented() -> None:
    seq = moving_sequence(20)
    seq[8:16, LEFT_START : LEFT_START + 63] = 0  # hand lost for 8 frames
    tracks = sequence_to_tracks(seq)
    finger = tracks["hand_l.index"][:, 0]
    assert abs(finger[7]) > 0 and np.allclose(finger[8], finger[7], atol=1e-6)  # held at first
    assert abs(finger[15]) < abs(finger[7])  # then relaxed toward rest
    assert not sequence_to_tracks(moving_sequence(20, with_hand=False))["hand_l.index"].any()


def test_unwrap_avoids_jumps_between_frames() -> None:
    tracks = sequence_to_tracks(moving_sequence(30))
    for b, a in tracks.items():
        assert np.abs(np.diff(a, axis=0)).max() < 1.0, b


def test_duration_limit_and_input_validation() -> None:
    with pytest.raises(ValueError, match="over the"):
        make(moving_sequence(700))
    with pytest.raises(ValueError):
        make(np.zeros((1, 225)))


def test_cli_writes_a_valid_clip_and_reports_errors(tmp_path, capsys) -> None:
    np.save(tmp_path / "s.npy", moving_sequence(16))
    import sys

    argv = sys.argv
    try:
        sys.argv = ["make_clip", "--features", str(tmp_path / "s.npy"), "--gloss", "hello", "--out", str(tmp_path / "o" / "hello.json")]
        assert make_clip_main() == 0
        clip = json.loads((tmp_path / "o" / "hello.json").read_text())
        ClipFile.model_validate(clip)
        assert clip["source"]["review_status"] == "not_signer_reviewed"
        assert "UNREVIEWED" in clip["source"]["description"] and "unresolved" in clip["source"]["license"]
        sys.argv = ["make_clip", "--features", str(tmp_path / "missing.npy"), "--gloss", "x", "--out", str(tmp_path / "x.json")]
        assert make_clip_main() == 2
    finally:
        sys.argv = argv
