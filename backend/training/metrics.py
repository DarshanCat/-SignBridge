import numpy as np


def confusion_matrix(y_true: np.ndarray, y_pred: np.ndarray, n: int) -> np.ndarray:
    cm = np.zeros((n, n), dtype=np.int64)
    np.add.at(cm, (y_true, y_pred), 1)
    return cm


def classification_report(y_true: np.ndarray, y_pred: np.ndarray, classes: list[str]) -> dict:
    """Accuracy, macro-F1 (over classes with test support) and per-class precision/recall/F1."""
    cm = confusion_matrix(y_true, y_pred, len(classes))
    per_class = {}
    f1s, ps, rs = [], [], []
    for i, name in enumerate(classes):
        tp = int(cm[i, i])
        fp = int(cm[:, i].sum() - tp)
        fn = int(cm[i, :].sum() - tp)
        support = int(cm[i, :].sum())
        p = tp / (tp + fp) if tp + fp else 0.0
        r = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * p * r / (p + r) if p + r else 0.0
        per_class[name] = {"precision": p, "recall": r, "f1": f1, "support": support}
        if support:
            f1s.append(f1)
            ps.append(p)
            rs.append(r)
    return {
        "accuracy": float((y_true == y_pred).mean()) if len(y_true) else 0.0,
        "macro_f1": float(np.mean(f1s)) if f1s else 0.0,
        "macro_precision": float(np.mean(ps)) if ps else 0.0,
        "macro_recall": float(np.mean(rs)) if rs else 0.0,
        "num_classes_with_support": len(f1s),
        "per_class": per_class,
        "confusion_matrix": cm.tolist(),
        "num_samples": int(len(y_true)),
    }
