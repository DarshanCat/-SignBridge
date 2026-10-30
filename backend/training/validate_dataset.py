"""Validate a processed dataset directory. Run from backend/:

    python -m training.validate_dataset --dir ..\\data\\processed\\<dataset>

Expects manifest.csv (path,label,signer_id), the .npy files it names, and dataset_info.json.
Datasets flagged consent_required must also have consent.csv (signer_id,consent_date,scope).
"""

import argparse
import csv
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np

from app.recognition.landmarks import FEATURE_DIM
from training.data import MIN_SIGNERS, DatasetError, read_manifest
from training.dataset_info import read_dataset_info

MIN_SAMPLES_PER_CLASS = 5


def read_consented_signers(path: Path) -> set[str]:
    if not path.is_file():
        raise DatasetError("consent.csv is required for this dataset but was not found.")
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if not {"signer_id", "consent_date", "scope"} <= set(reader.fieldnames or []):
            raise DatasetError("consent.csv needs columns signer_id,consent_date,scope")
        return {r["signer_id"].strip() for r in reader if r["consent_date"].strip() and r["scope"].strip()}


def validate(directory: Path, exclude_paths: frozenset[Path] = frozenset()) -> dict:
    """Return a report dict; raise DatasetError for blocking problems. Soft issues go in `warnings`."""
    info = read_dataset_info(directory)
    samples = [s for s in read_manifest(directory / "manifest.csv") if s.path not in exclude_paths]  # excluded files (e.g. the test split in pilot runs) are not opened

    if info.consent_required:
        missing = {s.signer for s in samples} - read_consented_signers(directory / "consent.csv")
        if missing:
            raise DatasetError(f"No consent record for signer(s): {sorted(missing)}")

    warnings: list[str] = []
    bad_files: list[str] = []
    lengths: list[int] = []
    hashes: dict[str, list[str]] = {}
    for s in samples:
        hashes.setdefault(hashlib.sha256(s.path.read_bytes()).hexdigest(), []).append(s.path.name)
        arr = np.load(s.path)
        lengths.append(int(arr.shape[0]))
        if arr.ndim != 2 or arr.shape[1] != FEATURE_DIM or arr.shape[0] < 1:
            bad_files.append(f"{s.path.name}: bad shape {arr.shape}")
        elif not np.isfinite(arr).all():
            bad_files.append(f"{s.path.name}: non-finite values")
    if bad_files:
        raise DatasetError(f"{len(bad_files)} invalid feature file(s), first: {bad_files[0]}")

    duplicates = [names for names in hashes.values() if len(names) > 1]
    if duplicates:
        warnings.append(f"{len(duplicates)} group(s) of identical feature files (possible duplicate samples), first: {duplicates[0][:3]}")
    per_class = Counter(s.label for s in samples)
    per_signer = Counter(s.signer for s in samples)
    signers = {s.signer for s in samples}
    if len(signers) < MIN_SIGNERS:
        warnings.append(f"Only {len(signers)} signer(s); signer-independent training needs at least {MIN_SIGNERS}.")
    few = sorted(c for c, n in per_class.items() if n < MIN_SAMPLES_PER_CLASS)
    if few:
        warnings.append(f"{len(few)} class(es) have fewer than {MIN_SAMPLES_PER_CLASS} samples: {few[:10]}")

    return {
        "dataset": info.name,
        "license": info.license,
        "source_url": info.source_url,
        "num_samples": len(samples),
        "num_classes": len(per_class),
        "num_signers": len(signers),
        "samples_per_class": dict(sorted(per_class.items())),
        "samples_per_signer": dict(sorted(per_signer.items())),
        "sequence_length_frames": {"min": min(lengths), "median": int(np.median(lengths)), "max": max(lengths)},
        "duplicate_groups": len(duplicates),
        "predefined_split": all(s.split for s in samples),
        "samples_per_class_min": min(per_class.values()),
        "samples_per_class_max": max(per_class.values()),
        "warnings": warnings,
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--dir", type=Path, required=True)
    p.add_argument("--report", type=Path, help="write the full data-quality report as JSON")
    a = p.parse_args()
    try:
        report = validate(a.dir)
    except DatasetError as exc:
        print(f"INVALID: {exc}", file=sys.stderr)
        return 2
    if a.report:
        a.report.parent.mkdir(parents=True, exist_ok=True)
        a.report.write_text(json.dumps(report, indent=2), encoding="utf-8")
    for k, v in report.items():
        if k not in ("warnings", "samples_per_class", "samples_per_signer"):
            print(f"{k}: {v}")
    for w in report["warnings"]:
        print(f"WARNING: {w}")
    print("Dataset structure is valid." if not report["warnings"] else "Dataset is valid with warnings.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
