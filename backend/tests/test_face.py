"""Face block: the 50 point list matches the browser's, the block is normalized like the body, and the models accept body plus face."""

import re
from pathlib import Path

import numpy as np
import pytest

from app.recognition.artifacts import ModelConfig, load_artifacts, save_artifacts
from app.recognition.face import FACE_DIM, FACE_INDICES, FACE_POINTS, face_block, resample_block, select_face
from app.recognition.landmarks import FEATURE_DIM
from app.recognition.models import build_model
from app.recognition.preprocess import prepare_sequence, prepare_sequence_full
from app.schemas.landmarks import LandmarkFrame, Point
from training.data import DatasetError
from training.dataset import load_store
from training.data import Sample

TS = Path(__file__).resolve().parents[2] / "frontend" / "src" / "lib" / "faceIndices.ts"


def pts(n, f=lambda i: (i, 0.0, 0.0)):
    return [Point(x=f(i)[0], y=f(i)[1], z=f(i)[2]) for i in range(n)]


def pose(shoulder_gap=0.2):
    p = pts(33, lambda i: (0.5, 0.5, 0.0))
    p[11] = Point(x=0.6, y=0.5, z=0.0)
    p[12] = Point(x=0.6 - shoulder_gap, y=0.5, z=0.0)
    return p


def test_fifty_unique_points_and_same_list_as_the_browser() -> None:
    assert FACE_POINTS == 50 and len(set(FACE_INDICES)) == 50 and FACE_DIM == 150
    assert all(0 <= i < 468 for i in FACE_INDICES)
    nums = re.sub(r"//.*", "", re.search(r"FACE_INDICES[^=]*=\s*\[(.*?)\];", TS.read_text(encoding="utf-8"), re.S).group(1))
    assert tuple(int(x) for x in re.findall(r"\d+", nums)) == FACE_INDICES


def test_select_face_and_block_normalization() -> None:
    full = pts(468, lambda i: (i / 1000, 0.3, 0.1))
    sel = select_face(full)
    assert len(sel) == 50 and sel[0].x == pytest.approx(FACE_INDICES[0] / 1000)
    assert select_face(None) is None and select_face(full[:10]) is None
    block = face_block(LandmarkFrame(pose=pose(0.2), face=sel))
    assert block.shape == (FACE_DIM,) and block.dtype == np.float32
    # origin = shoulder midpoint (0.5, 0.5, 0), scale = shoulder width 0.2
    assert block[0] == pytest.approx((FACE_INDICES[0] / 1000 - 0.5) / 0.2, abs=1e-5)
    assert block[1] == pytest.approx((0.3 - 0.5) / 0.2, abs=1e-5)


def test_missing_or_bad_input_gives_zeros() -> None:
    sel = pts(50)
    assert not face_block(LandmarkFrame(pose=pose(), face=None)).any()
    assert not face_block(LandmarkFrame(pose=None, face=sel)).any()
    assert not face_block(LandmarkFrame(pose=pose(0.0), face=sel)).any()  # shoulders on top of each other
    assert not face_block(LandmarkFrame(pose=pose(), face=sel[:10])).any()


def test_resample_block_and_full_preprocessing() -> None:
    b = np.arange(10 * 4, dtype=np.float32).reshape(10, 4)
    r = resample_block(b, 32)
    assert r.shape == (32, 4) and np.allclose(r[0], b[0]) and np.allclose(r[-1], b[-1])
    rng = np.random.default_rng(0)
    body = rng.random((17, FEATURE_DIM)).astype(np.float32)
    face = rng.random((17, FACE_DIM)).astype(np.float32)
    full = prepare_sequence_full(np.concatenate([body, face], axis=1), 32, 3)
    assert full.shape == (32, FEATURE_DIM + FACE_DIM)
    assert np.allclose(full[:, :FEATURE_DIM], prepare_sequence(body, 32, 3))  # the body part is exactly the old path
    assert np.allclose(prepare_sequence_full(body, 32, 3), prepare_sequence(body, 32, 3))  # body only input unchanged


def test_load_store_with_face_checks_shapes(tmp_path: Path) -> None:
    (tmp_path / "f").mkdir()
    body = np.zeros((9, FEATURE_DIM), np.float32)
    np.save(tmp_path / "a.npy", body)
    s = [Sample(tmp_path / "a.npy", "x", "u", "train")]
    with pytest.raises(DatasetError, match="face block missing"):
        load_store(s, ["x"], tmp_path / "f")
    np.save(tmp_path / "f" / "a.npy", np.zeros((8, FACE_DIM), np.float32))
    with pytest.raises(DatasetError, match="expected shape"):
        load_store(s, ["x"], tmp_path / "f")
    np.save(tmp_path / "f" / "a.npy", np.zeros((9, FACE_DIM), np.float32))
    assert load_store(s, ["x"], tmp_path / "f").sequences[0].shape == (9, FEATURE_DIM + FACE_DIM)
    assert load_store(s, ["x"]).sequences[0].shape == (9, FEATURE_DIM)


@pytest.mark.parametrize("arch", ["cnn", "bigru", "transformer"])
def test_a_face_model_saves_loads_and_runs(tmp_path: Path, arch: str) -> None:
    cfg = ModelConfig(["a", "b"], FEATURE_DIM + FACE_DIM, 32, 16, 1, 0.0, arch, 2, 3, True)
    model = build_model(cfg)
    save_artifacts(model, cfg, tmp_path)
    m, c = load_artifacts(tmp_path)
    assert c.face and c.feature_dim == FEATURE_DIM + FACE_DIM
    import torch

    assert m.eval()(torch.zeros(1, 32, FEATURE_DIM + FACE_DIM)).shape == (1, 2)


def test_a_model_with_the_wrong_width_is_refused(tmp_path: Path) -> None:
    from app.recognition.artifacts import ModelLoadError

    cfg = ModelConfig(["a", "b"], FEATURE_DIM + FACE_DIM, 32, 16, 1, 0.0, "cnn", 2, 0, False)  # face width but face flag off
    save_artifacts(build_model(cfg), cfg, tmp_path)
    with pytest.raises(ModelLoadError):
        load_artifacts(tmp_path)


def test_the_schema_accepts_an_optional_face() -> None:
    assert LandmarkFrame(pose=None, face=pts(50)).face is not None
    assert LandmarkFrame().face is None
    with pytest.raises(Exception):
        LandmarkFrame(face=pts(51))
