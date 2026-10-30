"""Manifest loading and signer-independent splitting.

Manifest CSV columns: path,label,signer_id. `path` is relative to the manifest and points to a
.npy file holding a (T, 225) normalized feature sequence (see app.recognition.landmarks).
"""

import csv
import random
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from app.recognition.landmarks import FEATURE_DIM
from app.recognition.preprocess import resample_sequence

REQUIRED_COLUMNS = {"path", "label", "signer_id"}
MIN_SIGNERS = 3


class DatasetError(Exception):
    pass


@dataclass(frozen=True)
class Sample:
    path: Path
    label: str
    signer: str
    split: str | None = None


def read_manifest(manifest: Path) -> list[Sample]:
    if not manifest.is_file():
        raise DatasetError(f"Manifest not found: {manifest}")
    with manifest.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        missing = REQUIRED_COLUMNS - set(reader.fieldnames or [])
        if missing:
            raise DatasetError(f"Manifest is missing columns: {sorted(missing)}")
        samples = [
            Sample(manifest.parent / r["path"], r["label"].strip(), r["signer_id"].strip(), (r.get("split") or "").strip() or None)
            for r in reader
        ]
    if not samples:
        raise DatasetError("Manifest has no rows.")
    absent = [s.path for s in samples if not s.path.is_file()]
    if absent:
        raise DatasetError(f"{len(absent)} sample file(s) not found, first: {absent[0]}")
    if any(not s.label or not s.signer for s in samples):
        raise DatasetError("Every row needs a non-empty label and signer_id.")
    return samples


def split_samples(samples: list[Sample], seed: int) -> tuple[dict[str, list[Sample]], str]:
    """Use the manifest's own `split` column when every row has one (author-provided split), else split by signer.

    Returns (splits, method). A predefined split is used as given: its signer independence is NOT verified here.
    """
    if all(s.split for s in samples):
        names = {s.split for s in samples}
        if not names <= {"train", "val", "test"} or not {"train", "val", "test"} <= names:
            raise DatasetError(f"split column must use train, val and test (all three); found {sorted(names)}")
        return {k: [s for s in samples if s.split == k] for k in ("train", "val", "test")}, "predefined"
    if any(s.split for s in samples):
        raise DatasetError("split column is filled for only some rows; fill every row or leave it empty")
    return split_by_signer(samples, seed), "signer-disjoint"


def split_by_signer(
    samples: list[Sample], seed: int, val_frac: float = 0.2, test_frac: float = 0.2
) -> dict[str, list[Sample]]:
    """Signer-disjoint train/val/test split. Refuses datasets with too few signers."""
    signers = sorted({s.signer for s in samples})
    if len(signers) < MIN_SIGNERS:
        raise DatasetError(
            f"Signer-independent evaluation needs at least {MIN_SIGNERS} signers; found {len(signers)}."
        )
    rng = random.Random(seed)
    rng.shuffle(signers)
    n_test = max(1, round(len(signers) * test_frac))
    n_val = max(1, round(len(signers) * val_frac))
    groups = {"test": signers[:n_test], "val": signers[n_test : n_test + n_val], "train": signers[n_test + n_val :]}
    if not groups["train"]:
        raise DatasetError("Not enough signers left for training after the split.")
    return {k: [s for s in samples if s.signer in set(v)] for k, v in groups.items()}


def load_arrays(samples: list[Sample], classes: list[str], seq_len: int) -> tuple[np.ndarray, np.ndarray]:
    index = {c: i for i, c in enumerate(classes)}
    xs, ys = [], []
    for s in samples:
        arr = np.load(s.path)
        if arr.ndim != 2 or arr.shape[1] != FEATURE_DIM:
            raise DatasetError(f"{s.path}: expected shape (T, {FEATURE_DIM}), got {arr.shape}")
        xs.append(resample_sequence(arr, seq_len))
        ys.append(index[s.label])
    return np.stack(xs), np.array(ys, dtype=np.int64)
