"""Train the 1D CNN, BiGRU and Transformer on the SAME split and seed and write one comparison. Run from backend/:

    python -m training.compare_models --manifest <manifest.csv> --out <runs dir> --results ..\\docs\\evaluation\\results.md [--augment]

The best model is chosen by VALIDATION macro-F1 (never by test); its folder is copied to <out>/best (weights + labels.json).
Test numbers are reported for all three, from the held-out test split, each once.
"""

import argparse
import json
import shutil
import sys
from pathlib import Path

from app.recognition.models import ARCHITECTURES
from training.data import DatasetError
from training.train import train


def pick_best(reports: dict[str, dict]) -> str:
    return max(reports, key=lambda a: reports[a]["results"]["val"]["macro_f1"])


def results_markdown(reports: dict[str, dict], best: str) -> str:
    any_r = next(iter(reports.values()))
    lines = [
        "# Model comparison results",
        "",
        f"Split: {any_r['split_method']}. Signer independence is unverified (no signer IDs). Sample counts: {any_r['sample_counts']}.",
        f"Dataset: {any_r['dataset']['name']}. Licence: {any_r['dataset']['license']}.",
        f"Seed {any_r['hyperparameters']['seed']}; every model uses the same split, seed, preprocessing and augmentation setting.",
        "",
        f"Best by validation macro-F1: **{best}**. Test numbers below come from the held-out test split.",
        "",
        "| Model | Params | Epochs run | Val macro-F1 | Test top-1 | Test top-5 | Test macro-F1 | Test macro-P | Test macro-R |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for arch, r in reports.items():
        v, t = r["results"]["val"], r["results"]["test"]
        lines.append(
            f"| {arch} | {r['parameters']} | {r['hyperparameters']['epochs_run']} | {v['macro_f1']:.4f} | {t['top1_accuracy']:.4f} | "
            f"{t['top5_accuracy']:.4f} | {t['macro_f1']:.4f} | {t['macro_precision']:.4f} | {t['macro_recall']:.4f} |"
        )
    lines += ["", "## Accuracy versus coverage (test, best model)", "", "| Threshold | Coverage | Accuracy on answered | Unrecognized |", "|---|---|---|---|"]
    for c in reports[best]["results"]["test"]["accuracy_vs_coverage"]:
        acc = "n/a" if c["accuracy_on_answered"] is None else f"{c['accuracy_on_answered']:.4f}"
        lines.append(f"| {c['threshold']:.2f} | {c['coverage']:.4f} | {acc} | {c['unrecognized']} |")
    lines += [
        "",
        "Per class accuracy and the confusion matrix for each model are in `<run>/metrics.json` (keys `per_class_accuracy`, `confusion_matrix`).",
        f"Classes with no training sample: {any_r['classes_missing_from_train']}.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--manifest", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--results", type=Path, required=True)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--epochs", type=int, default=60)
    p.add_argument("--augment", action="store_true")
    p.add_argument("--class-weights", action="store_true")
    p.add_argument("--threads", type=int, default=None)
    a = p.parse_args()
    reports: dict[str, dict] = {}
    try:
        for arch in ARCHITECTURES:
            print(f"training {arch} ...", flush=True)
            reports[arch] = train(
                a.manifest, a.out / arch, arch=arch, seed=a.seed, epochs=a.epochs, augment=a.augment,
                class_weights=a.class_weights, num_threads=a.threads,
            )
            t = reports[arch]["results"]["test"]
            print(f"  {arch}: test top1={t['top1_accuracy']:.4f} macro_f1={t['macro_f1']:.4f}", flush=True)
    except DatasetError as exc:
        print(f"Dataset error: {exc}", file=sys.stderr)
        return 2
    best = pick_best(reports)
    best_dir = a.out / "best"
    if best_dir.exists():
        shutil.rmtree(best_dir)
    shutil.copytree(a.out / best, best_dir)
    (best_dir / "BEST_ARCH.txt").write_text(best, encoding="utf-8")
    a.results.parent.mkdir(parents=True, exist_ok=True)
    a.results.write_text(results_markdown(reports, best), encoding="utf-8")
    (a.out / "summary.json").write_text(json.dumps({"best": best, "val_macro_f1": {k: v["results"]["val"]["macro_f1"] for k, v in reports.items()}}, indent=2), encoding="utf-8")
    print(f"best by validation macro-F1: {best}; results written to {a.results}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
