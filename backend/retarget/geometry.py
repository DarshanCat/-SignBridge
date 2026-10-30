"""Rotation helpers and forward kinematics for the SignBridge rig (three.js conventions).

Rig coordinates: x toward the signer's left (screen right), y up, z toward the camera. Landmarks (MediaPipe image space: x right,
y down, z depth with smaller values nearer the camera) convert with (x, -y, -z). Euler angles use three.js order XYZ, so the rotation
matrix is Rx(a) @ Ry(b) @ Rz(c), exactly as `Object3D.rotation.set(a, b, c)` applies them in the avatar.
"""

import numpy as np

REST_DIR = np.array([0.0, -1.0, 0.0])  # every limb bone points down along local -y in the rest pose
EPS = 1e-9


def landmarks_to_rig(points: np.ndarray) -> np.ndarray:
    """(..., 3) MediaPipe normalized landmarks to rig axes."""
    out = np.array(points, dtype=np.float64, copy=True)
    out[..., 1] *= -1.0
    out[..., 2] *= -1.0
    return out


def unit(v: np.ndarray) -> np.ndarray:
    n = np.linalg.norm(v)
    return v / n if n > EPS else v


def rot_x(a: float) -> np.ndarray:
    c, s = np.cos(a), np.sin(a)
    return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])


def rot_y(a: float) -> np.ndarray:
    c, s = np.cos(a), np.sin(a)
    return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])


def rot_z(a: float) -> np.ndarray:
    c, s = np.cos(a), np.sin(a)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])


def euler_to_matrix(e: tuple[float, float, float]) -> np.ndarray:
    """three.js Euler XYZ: R = Rx @ Ry @ Rz."""
    return rot_x(e[0]) @ rot_y(e[1]) @ rot_z(e[2])


def matrix_to_euler(m: np.ndarray) -> tuple[float, float, float]:
    """Inverse of euler_to_matrix (three.js Euler.setFromRotationMatrix, order XYZ)."""
    b = float(np.arcsin(np.clip(m[0, 2], -1.0, 1.0)))
    if abs(m[0, 2]) < 0.9999999:
        a = float(np.arctan2(-m[1, 2], m[2, 2]))
        c = float(np.arctan2(-m[0, 1], m[0, 0]))
    else:  # gimbal lock
        a = float(np.arctan2(m[2, 1], m[1, 1]))
        c = 0.0
    return a, b, c


def rotation_between(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Smallest rotation matrix taking unit vector a to unit vector b (no roll about the axis)."""
    a, b = unit(a), unit(b)
    v = np.cross(a, b)
    s, c = np.linalg.norm(v), float(np.dot(a, b))
    if s < EPS:
        if c > 0:
            return np.eye(3)
        axis = unit(np.cross(a, [1.0, 0.0, 0.0])) if abs(a[0]) < 0.9 else unit(np.cross(a, [0.0, 1.0, 0.0]))
        return 2.0 * np.outer(axis, axis) - np.eye(3)  # 180 degrees about any axis perpendicular to a
    k = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]])
    return np.eye(3) + k + k @ k * ((1 - c) / (s * s))


def frame_rotation(from_f: np.ndarray, from_u: np.ndarray, to_f: np.ndarray, to_u: np.ndarray) -> np.ndarray:
    """Rotation taking the frame (forward f, side u) to the frame (to_f, to_u). u is orthogonalized against f."""
    def basis(f: np.ndarray, u: np.ndarray) -> np.ndarray:
        y = unit(f)
        x = unit(u - np.dot(u, y) * y)
        z = np.cross(x, y)
        return np.stack([x, y, z], axis=1)
    return basis(to_f, to_u) @ basis(from_f, from_u).T


def angle_between(a: np.ndarray, b: np.ndarray) -> float:
    a, b = unit(a), unit(b)
    return float(np.arccos(np.clip(np.dot(a, b), -1.0, 1.0)))
