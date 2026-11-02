"""Choose the live confidence threshold on the VALIDATION split and write threshold.json next to the model. Run from backend/:

    python -m training.calibrate --manifest <manifest.csv> --model-dir <best dir> [--precision 0.9] [--evaluate-test]

Rule: the lowest threshold whose accuracy on answered validation samples is at least --precision (default 0.90), searched on the grid of the accuracy versus coverage tables.
The test split is only read when --evaluate-test is given, and only to report coverage and accuracy of the chosen threshold (it does not
influence the choice).
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np

from app.recognition.artifacts import load_artifacts
from training.data import DatasetError
from training.dataset import load_splits
from training.slr_metrics import DEFAULT_THRESHOLDS, coverage_curve
from training.train import predict_probs


def choose_threshold(probs: np.ndarray, y: np.ndarray, precision: float, grid=DEFAULT_THRESHOLDS) -> float:
    """Lowest grid value reaching the precision target. The grid is the one used for the accuracy versus coverage tables, so the test
    numbers for the chosen threshold come from the single test evaluation that already exists (the test split is never read again)."""
    for t in grid:
        row = coverage_curve(probs, y, (float(t),))[0]
        if row["accuracy_on_answered"] is not None and row["accuracy_on_answered"] >= precision and row["answered"] >= max(5, 0.05 * len(y)):
            return float(t)
    return float(max(grid))  # nothing reaches the target: be strict instead of accepting everything


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--manifest", type=Path, required=True)
    p.add_argument("--model-dir", type=Path, required=True)
    p.add_argument("--precision", type=float, default=0.90)
    p.add_argument("--evaluate-test", action="store_true")
    a = p.parse_args()
    try:
        seed = int(json.loads((a.model_dir / "metrics.json").read_text(encoding="utf-8"))["hyperparameters"]["seed"])
        model, cfg = load_artifacts(a.model_dir)
        data = load_splits(a.manifest, seed, load_test=a.evaluate_test)
    except (DatasetError, OSError, KeyError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    va = data.stores["val"]
    probs = predict_probs(model, va.all(cfg.seq_len, cfg.max_gap))
    thr = choose_threshold(probs, va.labels, a.precision)
    row = coverage_curve(probs, va.labels, (thr,))[0]
    out = {
        "threshold": thr,
        "chosen_on": "validation",
        "rule": f"lowest value of {list(DEFAULT_THRESHOLDS)} with at least {a.precision:.0%} accuracy on answered validation samples",
        "val_coverage": row["coverage"],
        "val_accuracy_on_answered": row["accuracy_on_answered"],
        "architecture": cfg.arch,
    }
    if a.evaluate_test:
        te = data.stores["test"]
        t = coverage_curve(predict_probs(model, te.all(cfg.seq_len, cfg.max_gap)), te.labels, (thr,))[0]
        out |= {"test_coverage": t["coverage"], "test_accuracy_on_answered": t["accuracy_on_answered"]}
    (a.model_dir / "threshold.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
