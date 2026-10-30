"""Retarget one normalized landmark frame (225 features: pose 33, left hand 21, right hand 21) onto the 20 bone SignBridge rig.

What is recovered: shoulder and elbow direction (so the arm swings to the right place), forearm direction, hand orientation (from the
direction wrist to middle knuckle and the knuckle line index to pinky), and one curl angle per finger. What is NOT recovered: the roll of
the upper arm and forearm about their own axes (positions alone do not give it), finger spread, thumb opposition, the head, torso and face.
This is a geometric approximation, not motion capture, and every output needs visual and signer review.
"""

import numpy as np

from app.recognition.landmarks import HAND_POINTS, POSE_POINTS
from retarget.geometry import (
    REST_DIR, angle_between, frame_rotation, landmarks_to_rig, matrix_to_euler, rotation_between, unit,
)

POSE_END = POSE_POINTS * 3
LEFT_END = POSE_END + HAND_POINTS * 3
SIDES = {  # side: (shoulder, elbow, wrist pose index, hand block start, x sign of the side)
    "l": (11, 13, 15, POSE_END, 1.0),
    "r": (12, 14, 16, LEFT_END, -1.0),
}
FINGERS = {"thumb": (0, 1, 2, 3, 4), "index": (0, 5, 6, 7, 8), "middle": (0, 9, 10, 11, 12), "ring": (0, 13, 14, 15, 16), "pinky": (0, 17, 18, 19, 20)}
MAX_CURL = 2.4  # radians, limit for a single joint finger
BONES_PER_SIDE = ["upperArm", "foreArm", "hand", "hand.thumb", "hand.index", "hand.middle", "hand.ring", "hand.pinky"]


def _pose_point(x: np.ndarray, i: int) -> np.ndarray:
    return landmarks_to_rig(x[i * 3 : i * 3 + 3])


def _hand_points(x: np.ndarray, start: int) -> np.ndarray | None:
    block = x[start : start + HAND_POINTS * 3]
    if not block.any():  # an all zero block means the hand was not detected
        return None
    return landmarks_to_rig(block.reshape(HAND_POINTS, 3))


def finger_curl(hand: np.ndarray, chain: tuple[int, ...]) -> float:
    """Sum of the bend angles along wrist to knuckle to the three finger joints (0 for a straight finger)."""
    segs = [hand[chain[i + 1]] - hand[chain[i]] for i in range(len(chain) - 1)]
    return float(sum(angle_between(segs[i], segs[i + 1]) for i in range(len(segs) - 1)))


def frame_to_bones(x: np.ndarray) -> tuple[dict[str, tuple[float, float, float]], dict[str, bool]]:
    """Return ({bone: Euler XYZ radians}, {side: hand detected}) for one frame."""
    if x.shape != (225,):
        raise ValueError(f"expected 225 features, got {x.shape}")
    bones: dict[str, tuple[float, float, float]] = {}
    present: dict[str, bool] = {}
    for side, (sh, el, wr, hstart, m) in SIDES.items():
        p_sh, p_el, p_wr = _pose_point(x, sh), _pose_point(x, el), _pose_point(x, wr)
        if np.linalg.norm(p_el - p_sh) < 1e-6 or np.linalg.norm(p_wr - p_el) < 1e-6:
            raise ValueError("degenerate arm landmarks")
        w_upper = rotation_between(REST_DIR, unit(p_el - p_sh))
        local_fore = w_upper.T @ unit(p_wr - p_el)
        r_fore = rotation_between(REST_DIR, local_fore)
        w_fore = w_upper @ r_fore
        bones[f"upperArm_{side}"] = matrix_to_euler(w_upper)
        bones[f"foreArm_{side}"] = matrix_to_euler(r_fore)

        hand = _hand_points(x, hstart)
        present[side] = hand is not None
        if hand is None:
            bones[f"hand_{side}"] = (0.0, 0.0, 0.0)
            for name in FINGERS:
                bones[f"hand_{side}.{name}"] = (0.0, 0.0, 0.0)
            continue
        fwd = unit(hand[9] - hand[0])
        side_vec = hand[17] - hand[5]  # index knuckle to pinky knuckle
        rest_side = np.array([-m, 0.0, 0.0])  # rig rest: thumb outward, so index to pinky points toward the body
        w_hand = frame_rotation(REST_DIR, rest_side, fwd, side_vec)
        bones[f"hand_{side}"] = matrix_to_euler(w_fore.T @ w_hand)
        for name, chain in FINGERS.items():
            curl = min(finger_curl(hand, chain), MAX_CURL)
            bones[f"hand_{side}.{name}"] = (-curl, 0.0, 0.0)  # negative x curls toward the palm in the rig
    return bones, present
