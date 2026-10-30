"""Metrics computed from class probabilities: top-k, per-class accuracy and accuracy versus coverage at confidence thresholds."""

import numpy as np

from training.metrics import classification_report

DEFAULT_THRESHOLDS = (0.0, 0.3, 0.5, 0.7, 0.8, 0.9, 0.95)


def topk_accuracy(probs: np.ndarray, y: np.ndarray, k: int) -> float:
    if len(y) == 0:
        return 0.0
    k = min(k, probs.shape[1])
    top = np.argpartition(-probs, k - 1, axis=1)[:, :k]
    return float((top == y[:, None]).any(axis=1).mean())


def per_class_accuracy(pred: np.ndarray, y: np.ndarray, classes: list[str]) -> dict[str, dict]:
    out = {}
    for i, name in enumerate(classes):
        mask = y == i
        n = int(mask.sum())
        out[name] = {"support": n, "accuracy": float((pred[mask] == i).mean()) if n else None}
    return out


def coverage_curve(probs: np.ndarray, y: np.ndarray, thresholds=DEFAULT_THRESHOLDS) -> list[dict]:
    """For each threshold: share of samples answered (coverage), accuracy on those answered, and the count left UNRECOGNIZED.

    A sample is answered when its top probability reaches the threshold; otherwise it is reported as unrecognized, not forced.
    """
    conf = probs.max(axis=1)
    pred = probs.argmax(axis=1)
    rows = []
    for t in thresholds:
        keep = conf >= t
        n = int(keep.sum())
        rows.append({
            "threshold": float(t),
            "coverage": float(n / len(y)) if len(y) else 0.0,
            "accuracy_on_answered": float((pred[keep] == y[keep]).mean()) if n else None,
            "answered": n,
            "unrecognized": int(len(y) - n),
        })
    return rows


def full_report(probs: np.ndarray, y: np.ndarray, classes: list[str], thresholds=DEFAULT_THRESHOLDS) -> dict:
    pred = probs.argmax(axis=1)
    report = classification_report(y, pred, classes)
    report["top1_accuracy"] = report["accuracy"]
    report["top5_accuracy"] = topk_accuracy(probs, y, 5)
    report["per_class_accuracy"] = per_class_accuracy(pred, y, classes)
    report["accuracy_vs_coverage"] = coverage_curve(probs, y, thresholds)
    return report
