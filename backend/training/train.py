"""Train a sign classifier (1D CNN, BiGRU or Transformer). Run from backend/:  python -m training.train --manifest <csv> --arch bigru

Training is kept separate from the API. Writes isl_model.pt, labels.json (class map, architecture, preprocessing) and metrics.json.
The manifest's predefined split is used when present; early stopping and model selection use only the validation split.
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
from app.recognition.models import ARCHITECTURES, build_model
from training.augment import AugmentConfig, DeployAugmentConfig
from training.data import DatasetError, read_manifest, split_samples
from training.dataset import load_splits
from training.dataset_info import read_dataset_info
from training.slr_metrics import full_report
from training.validate_dataset import validate


def predict_probs(model: nn.Module, x: np.ndarray, batch: int = 256) -> np.ndarray:
    model.eval()
    out = []
    with torch.no_grad():
        for i in range(0, len(x), batch):
            out.append(torch.softmax(model(torch.from_numpy(x[i : i + batch])), dim=-1).numpy())
    return np.concatenate(out)


def train(
    manifest: Path, out_dir: Path, *, arch: str = "bigru", seed: int = 0, epochs: int = 40, batch_size: int = 16,
    lr: float = 1e-3, seq_len: int = 32, hidden: int = 128, layers: int = 2, heads: int = 4, dropout: float = 0.3,
    patience: int = 8, noise_std: float = 0.01, class_weights: bool = False, augment: bool = False, max_gap: int = 0,
    num_threads: int | None = None, evaluate_test: bool = True, deploy_augment: bool = False,
) -> dict:
    if arch not in ARCHITECTURES:
        raise DatasetError(f"unknown architecture {arch!r}; expected one of {ARCHITECTURES}")
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if num_threads:
        torch.set_num_threads(num_threads)
    rng = np.random.default_rng(seed)

    info = read_dataset_info(manifest.parent)
    held_out: frozenset[Path] = frozenset()
    if not evaluate_test:  # pilot mode: the test files are not opened by validation either
        held_out = frozenset(s.path for s in split_samples(read_manifest(manifest), seed)[0]["test"])
    validate(manifest.parent, exclude_paths=held_out)  # refuses to train on a dataset that does not pass validation
    data = load_splits(manifest, seed, load_test=evaluate_test)  # evaluate_test=False: the test features are never read
    classes = data.classes
    tr, va = data.stores["train"], data.stores["val"]
    missing = [c for i, c in enumerate(classes) if i not in set(tr.labels.tolist())]

    config = ModelConfig(classes, FEATURE_DIM, seq_len, hidden, layers, dropout, arch, heads, max_gap)
    model = build_model(config)
    opt = torch.optim.Adam(model.parameters(), lr=lr)
    weight = None
    if class_weights:  # inverse-frequency weights from the TRAIN split only
        counts = np.bincount(tr.labels, minlength=len(classes)).astype(np.float32)
        weight = torch.from_numpy(counts.sum() / (len(classes) * np.maximum(counts, 1)))
    loss_fn = nn.CrossEntropyLoss(weight=weight)
    aug = AugmentConfig() if augment else None
    deploy = DeployAugmentConfig() if deploy_augment else None
    x_val = va.all(seq_len, max_gap)
    best_f1, best_state, stale, epochs_run = -1.0, None, 0, 0

    for _ in range(epochs):
        model.train()
        epochs_run += 1
        order = rng.permutation(len(tr))
        for i in range(0, len(order), batch_size):
            b = order[i : i + batch_size]
            xb = torch.from_numpy(tr.batch(b, seq_len, max_gap, rng, aug, deploy))
            xb = xb + noise_std * torch.randn_like(xb)
            opt.zero_grad()
            loss_fn(model(xb), torch.from_numpy(tr.labels[b])).backward()
            opt.step()
        val_f1 = full_report(predict_probs(model, x_val), va.labels, classes)["macro_f1"]
        if val_f1 > best_f1:
            best_f1, stale = val_f1, 0
            best_state = {k: v.clone() for k, v in model.state_dict().items()}
        else:
            stale += 1
            if stale >= patience:
                break

    assert best_state is not None
    model.load_state_dict(best_state)
    results = {"val": full_report(predict_probs(model, x_val), va.labels, classes)}
    if evaluate_test:
        te = data.stores["test"]
        results["test"] = full_report(predict_probs(model, te.all(seq_len, max_gap)), te.labels, classes)
    save_artifacts(model.eval(), config, out_dir)
    report = {
        "dataset": {"name": info.name, "license": info.license, "source_url": info.source_url},
        "results": results,
        "classes_missing_from_train": missing,
        "split_method": data.method,
        "split_signers": {k: sorted({s.signer for s in v}) for k, v in data.samples.items()},
        "sample_counts": {k: len(v) for k, v in data.samples.items()},
        "hyperparameters": {
            "arch": arch, "seed": seed, "epochs_max": epochs, "epochs_run": epochs_run, "batch_size": batch_size, "lr": lr,
            "seq_len": seq_len, "hidden": hidden, "layers": layers, "heads": heads, "dropout": dropout, "patience": patience,
            "noise_std": noise_std, "class_weights": class_weights, "augment": augment, "max_gap": max_gap, "deploy_augment": deploy_augment,
        },
        "parameters": int(sum(p.numel() for p in model.parameters())),
        "environment": {"python": platform.python_version(), "torch": torch.__version__, "platform": platform.platform()},
    }
    (out_dir / "metrics.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--manifest", type=Path, required=True)
    p.add_argument("--out", type=Path, default=Path("models"))
    p.add_argument("--arch", choices=ARCHITECTURES, default="bigru")
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--epochs", type=int, default=40)
    p.add_argument("--augment", action="store_true", help="landmark augmentation (rotation, scale, speed, temporal jitter)")
    p.add_argument("--deploy-augment", action="store_true", help="y scale, landmark noise and hand dropout (training.augment.DeployAugmentConfig)")
    p.add_argument("--max-gap", type=int, default=0, help="interpolate missing hand gaps up to this many frames")
    p.add_argument("--threads", type=int, default=None, help="limit torch CPU threads")
    p.add_argument("--class-weights", action="store_true", help="inverse-frequency loss weights (train split)")
    a = p.parse_args()
    try:
        report = train(
            a.manifest, a.out, arch=a.arch, seed=a.seed, epochs=a.epochs, class_weights=a.class_weights, augment=a.augment,
            max_gap=a.max_gap, num_threads=a.threads, deploy_augment=a.deploy_augment,
        )
    except DatasetError as exc:
        print(f"Dataset error: {exc}", file=sys.stderr)
        return 2
    t = report["results"]["test"]
    print(
        f"Test ({report['split_method']} split, {a.arch}): top1={t['top1_accuracy']:.3f} top5={t['top5_accuracy']:.3f} "
        f"macro_f1={t['macro_f1']:.3f} n={t['num_samples']}"
    )
    print(f"Artifacts and metrics.json written to {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
