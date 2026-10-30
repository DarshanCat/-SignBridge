"""Train the BiGRU sign classifier. Run from backend/:  python -m training.train --manifest <csv>

Training is kept separate from the API. Writes isl_model.pt, labels.json and metrics.json.
"""

import argparse
import json
import platform
import random
import sys
from pathlib import Path

import numpy as np
import torch
from torch import nn

from app.recognition.artifacts import ModelConfig, save_artifacts
from app.recognition.landmarks import FEATURE_DIM
from app.recognition.model import BiGRUClassifier
from training.dataset_info import read_dataset_info
from training.data import DatasetError, load_arrays, read_manifest, split_samples
from training.validate_dataset import validate
from training.metrics import classification_report


def _predict(model: nn.Module, x: np.ndarray) -> np.ndarray:
    model.eval()
    with torch.no_grad():
        return model(torch.from_numpy(x)).argmax(dim=-1).numpy()


def train(
    manifest: Path, out_dir: Path, *, seed: int = 0, epochs: int = 40, batch_size: int = 16, lr: float = 1e-3,
    seq_len: int = 32, hidden: int = 128, layers: int = 2, dropout: float = 0.3, patience: int = 8,
    noise_std: float = 0.01, class_weights: bool = False,
) -> dict:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)

    info = read_dataset_info(manifest.parent)
    validate(manifest.parent)  # refuses to train on a dataset that does not pass validation
    samples = read_manifest(manifest)
    splits, split_method = split_samples(samples, seed)
    classes = sorted({s.label for s in samples})
    data = {k: load_arrays(v, classes, seq_len) for k, v in splits.items() if v}
    if "val" not in data or "test" not in data:
        raise DatasetError("Validation and test splits must both be non-empty.")
    x_tr, y_tr = data["train"]
    train_classes = set(y_tr.tolist())
    missing = [c for i, c in enumerate(classes) if i not in train_classes]

    model = BiGRUClassifier(FEATURE_DIM, len(classes), hidden, layers, dropout)
    opt = torch.optim.Adam(model.parameters(), lr=lr)
    weight = None
    if class_weights:  # inverse-frequency weights from the TRAIN split only
        counts = np.bincount(y_tr, minlength=len(classes)).astype(np.float32)
        weight = torch.from_numpy(counts.sum() / (len(classes) * np.maximum(counts, 1)))
    loss_fn = nn.CrossEntropyLoss(weight=weight)
    best_f1, best_state, stale = -1.0, None, 0

    for _ in range(epochs):
        model.train()
        order = np.random.permutation(len(x_tr))
        for i in range(0, len(order), batch_size):
            b = order[i : i + batch_size]
            xb = torch.from_numpy(x_tr[b]) + noise_std * torch.randn(len(b), *x_tr.shape[1:])
            opt.zero_grad()
            loss_fn(model(xb), torch.from_numpy(y_tr[b])).backward()
            opt.step()
        val_f1 = classification_report(data["val"][1], _predict(model, data["val"][0]), classes)["macro_f1"]
        if val_f1 > best_f1:
            best_f1, stale = val_f1, 0
            best_state = {k: v.clone() for k, v in model.state_dict().items()}
        else:
            stale += 1
            if stale >= patience:
                break

    assert best_state is not None
    model.load_state_dict(best_state)
    results = {
        "val": classification_report(data["val"][1], _predict(model, data["val"][0]), classes),
        "test": classification_report(data["test"][1], _predict(model, data["test"][0]), classes),
    }
    config = ModelConfig(classes, FEATURE_DIM, seq_len, hidden, layers, dropout)
    save_artifacts(model.eval(), config, out_dir)
    report = {
        "dataset": {"name": info.name, "license": info.license, "source_url": info.source_url},
        "results": results,
        "classes_missing_from_train": missing,
        "split_method": split_method,
        "split_signers": {k: sorted({s.signer for s in v}) for k, v in splits.items()},
        "sample_counts": {k: len(v) for k, v in splits.items()},
        "hyperparameters": {
            "seed": seed, "epochs_max": epochs, "batch_size": batch_size, "lr": lr, "seq_len": seq_len,
            "hidden": hidden, "layers": layers, "dropout": dropout, "patience": patience, "noise_std": noise_std, "class_weights": class_weights,
        },
        "environment": {"python": platform.python_version(), "torch": torch.__version__, "platform": platform.platform()},
    }
    (out_dir / "metrics.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--manifest", type=Path, required=True)
    p.add_argument("--out", type=Path, default=Path("models"))
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--epochs", type=int, default=40)
    p.add_argument("--class-weights", action="store_true", help="inverse-frequency loss weights (train split)")
    a = p.parse_args()
    try:
        report = train(a.manifest, a.out, seed=a.seed, epochs=a.epochs, class_weights=a.class_weights)
    except DatasetError as exc:
        print(f"Dataset error: {exc}", file=sys.stderr)
        return 2
    t = report["results"]["test"]
    print(f"Test ({report['split_method']} split): accuracy={t['accuracy']:.3f} macro_f1={t['macro_f1']:.3f} n={t['num_samples']}")
    print(f"Artifacts and metrics.json written to {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
