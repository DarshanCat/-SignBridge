"""Dataset loader that reads a manifest path and serves split tensors for the sign classifiers."""

from dataclasses import dataclass
from pathlib import Path

import numpy as np

from app.recognition.landmarks import FEATURE_DIM
from app.recognition.face import FACE_DIM
from app.recognition.preprocess import prepare_sequence_full
from training.augment import AugmentConfig, DeployAugmentConfig, augment_sequence, deploy_augment
from training.data import DatasetError, Sample, read_manifest, split_samples


@dataclass
class SequenceStore:
    """Raw (unresampled) sequences with integer labels. Batches are prepared on demand so augmentation differs per epoch."""

    sequences: list[np.ndarray]
    labels: np.ndarray

    def __len__(self) -> int:
        return len(self.sequences)

    def batch(
        self, idx: np.ndarray, seq_len: int, max_gap: int = 0, rng: np.random.Generator | None = None,
        augment: AugmentConfig | None = None, deploy: DeployAugmentConfig | None = None,
    ) -> np.ndarray:
        rows = []
        for i in idx:
            seq = self.sequences[int(i)]
            if rng is not None and augment is not None:
                seq = augment_sequence(seq, rng, augment)
            if rng is not None and deploy is not None:
                seq = deploy_augment(seq, rng, deploy)
            rows.append(prepare_sequence_full(seq, seq_len, max_gap))
        return np.stack(rows)

    def all(self, seq_len: int, max_gap: int = 0) -> np.ndarray:
        return self.batch(np.arange(len(self)), seq_len, max_gap)


def load_store(samples: list[Sample], classes: list[str], face_dir: Path | None = None) -> SequenceStore:
    """face_dir: folder with one (T, FACE_DIM) file per sample (same file name as the feature file); the sequences then have FEATURE_DIM + FACE_DIM columns."""
    index = {c: i for i, c in enumerate(classes)}
    seqs, ys = [], []
    for s in samples:
        arr = np.load(s.path)
        if arr.ndim != 2 or arr.shape[1] != FEATURE_DIM or arr.shape[0] == 0:
            raise DatasetError(f"{s.path}: expected shape (T, {FEATURE_DIM}) with T > 0, got {arr.shape}")
        arr = arr.astype(np.float32)
        if face_dir is not None:
            f = face_dir / s.path.name
            if not f.is_file():
                raise DatasetError(f"face block missing for {s.path.name} in {face_dir}")
            face = np.load(f)
            if face.shape != (arr.shape[0], FACE_DIM):
                raise DatasetError(f"{f}: expected shape ({arr.shape[0]}, {FACE_DIM}), got {face.shape}")
            arr = np.concatenate([arr, face.astype(np.float32)], axis=1)
        seqs.append(arr)
        ys.append(index[s.label])
    return SequenceStore(seqs, np.array(ys, dtype=np.int64))


@dataclass
class SplitData:
    classes: list[str]
    method: str
    samples: dict[str, list[Sample]]
    stores: dict[str, SequenceStore]


def load_splits(manifest: Path, seed: int = 0, load_test: bool = True, face_dir: Path | None = None) -> SplitData:
    """Read a manifest path (relative file paths resolve against the manifest folder) and load train, val and test."""
    samples = read_manifest(manifest)
    splits, method = split_samples(samples, seed)
    classes = sorted({s.label for s in samples})
    empty = [k for k in ("train", "val", "test") if not splits.get(k)]
    if empty:
        raise DatasetError(f"empty split(s): {empty}")
    # load_test=False never reads the test feature files (used by pilot runs that must not touch the test split)
    return SplitData(classes, method, splits, {k: load_store(v, classes, face_dir) for k, v in splits.items() if load_test or k != "test"})
