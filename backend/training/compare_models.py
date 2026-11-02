"""Train the 1D CNN, BiGRU and Transformer on the SAME split and seed and write one comparison. Run from backend/:

    python -m training.compare_models --manifest <manifest.csv> --out <runs dir> --results ..\\docs\\evaluation\\results.md [--augment]

The best model is chosen by VALIDATION macro-F1 (never by test); its folder is copied to <out>/best (weights + labels.json).
Test numbers are reported for all three, from the held-out test split, each once.
"""

import argparse
import csv
import json
import shutil
import sys
from pathlib import Path

from app.recognition.models import ARCHITECTURES
from training.data import DatasetError
from training.train import train


def pick_best(reports: dict[str, dict]) -> str:
    return max(reports, key=lambda a: reports[a]["results"]["val"]["macro_f1"])


LABEL = "Authors' predefined split, signer independence not verified."


def confusion_csv(report: dict, classes: list[str], path: Path) -> None:
    """Full confusion matrix (rows: true class, columns: predicted class) as CSV."""
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["true/predicted", *classes])
        for name, row in zip(classes, report["confusion_matrix"]):
            w.writerow([name, *row])


def top_confusions(report: dict, classes: list[str], n: int = 15) -> list[tuple[str, str, int]]:
    cm = report["confusion_matrix"]
    pairs = [(classes[i], classes[j], int(c)) for i, row in enumerate(cm) for j, c in enumerate(row) if i != j and c > 0]
    return sorted(pairs, key=lambda t: -t[2])[:n]


def results_markdown(
    reports: dict[str, dict], best: str, confusion_files: dict[str, str] | None = None, threshold: dict | None = None,
    classes: list[str] | None = None,
) -> str:
    any_r = next(iter(reports.values()))
    lines = [
        "# Model comparison results",
        "",
        f"**{LABEL}**",
        "",
        f"Split: {any_r['split_method']}. Sample counts: {any_r['sample_counts']}.",
        f"Dataset: {any_r['dataset']['name']}. Licence: unresolved (CC BY 4.0 per Zenodo, CC BY-NC-SA 4.0 per a third party page); treated as "
        "CC BY-NC-SA 4.0, non-commercial only, with attribution (see DATA_NOTICE.md).",
        f"Seed {any_r['hyperparameters']['seed']}; every model uses the same split, seed, preprocessing and augmentation setting.",
        "Training settings (identical for all three, architecture aside): "
        + ", ".join(f"{k} {v}" for k, v in any_r["hyperparameters"].items() if k not in ("arch", "epochs_run", "seed"))
        + ". Model selection and early stopping used the validation split only; the test split was evaluated once per model.",
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
    lines += ["", "## Accuracy versus coverage (test split)", ""]
    for arch in reports:
        lines += [f"### {arch}", "", "| Threshold | Coverage | Accuracy on answered | Unrecognized |", "|---|---|---|---|"]
        for c in reports[arch]["results"]["test"]["accuracy_vs_coverage"]:
            acc = "n/a" if c["accuracy_on_answered"] is None else f"{c['accuracy_on_answered']:.4f}"
            lines.append(f"| {c['threshold']:.2f} | {c['coverage']:.4f} | {acc} | {c['unrecognized']} |")
        lines.append("")
    if threshold:
        row = next((c for c in reports[best]["results"]["test"]["accuracy_vs_coverage"] if abs(c["threshold"] - threshold["threshold"]) < 1e-9), None)
        tail = ""
        if row and row["accuracy_on_answered"] is not None:
            tail = (f" On the test split (the single evaluation reported above) this threshold gives coverage {row['coverage']:.4f} and accuracy on "
                    f"answered {row['accuracy_on_answered']:.4f}.")
        lines += [
            "## Confidence threshold used by the live recognizer",
            "",
            f"Chosen on the validation split of the best model ({threshold.get('rule', '')}): **{threshold['threshold']}**; validation coverage "
            f"{threshold.get('val_coverage', float('nan')):.4f}, validation accuracy on answered {threshold.get('val_accuracy_on_answered', float('nan')):.4f}."
            + tail + " Signs below it are returned as UNRECOGNIZED.",
            "",
        ]
    if classes:
        lines += ["## Per class accuracy (test split, best model)", "", "| Class | Test samples | Accuracy |", "|---|---|---|"]
        for name, v in reports[best]["results"]["test"]["per_class_accuracy"].items():
            if v["support"]:
                lines.append(f"| {name} | {v['support']} | {v['accuracy']:.3f} |")
        lines += ["", "## Most frequent confusions (test split, best model)", "", "| True class | Predicted as | Count |", "|---|---|---|"]
        lines += [f"| {x} | {y} | {n} |" for x, y, n in top_confusions(reports[best]["results"]["test"], classes)]
        lines.append("")
    if confusion_files:
        lines += ["## Full confusion matrices", ""] + [f"- {arch}: [{f}]({f})" for arch, f in confusion_files.items()] + [""]
    lines += [f"Classes with no training sample: {any_r['classes_missing_from_train']}.", ""]
    return "\n".join(lines)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--manifest", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--results", type=Path, required=True)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--epochs", type=int, default=60)
    p.add_argument("--augment", action="store_true")
    p.add_argument("--deploy-augment", action="store_true", help="y scale, landmark noise and hand dropout (training.augment.DeployAugmentConfig)")
    p.add_argument("--class-weights", action="store_true")
    p.add_argument("--reuse", action="store_true", help="do not train: rebuild results.md from the metrics.json files already in --out (no model is re-evaluated)")
    p.add_argument("--checkpoint", action="store_true", help="per epoch checkpoints in <out>/<arch>/ (checkpoint_last.pt, checkpoint_best.pt)")
    p.add_argument("--resume", action="store_true", help="continue each architecture from its checkpoint_last.pt (implies --checkpoint); a finished run is re-finalized, which evaluates the test split again")
    p.add_argument("--max-gap", type=int, default=0)
    p.add_argument("--patience", type=int, default=8)
    p.add_argument("--threshold-file", type=Path, help="threshold.json from training.calibrate, added to the results")
    p.add_argument("--threads", type=int, default=None)
    a = p.parse_args()
    reports: dict[str, dict] = {}
    try:
        for arch in ARCHITECTURES:
            if a.reuse:
                reports[arch] = json.loads((a.out / arch / "metrics.json").read_text(encoding="utf-8"))
                continue
            print(f"training {arch} ...", flush=True)
            reports[arch] = train(
                a.manifest, a.out / arch, arch=arch, seed=a.seed, epochs=a.epochs, augment=a.augment,
                class_weights=a.class_weights, num_threads=a.threads, max_gap=a.max_gap, patience=a.patience, deploy_augment=a.deploy_augment,
                checkpoint=a.checkpoint or a.resume, resume=a.resume,
            )
            t = reports[arch]["results"]["test"]
            print(f"  {arch}: test top1={t['top1_accuracy']:.4f} macro_f1={t['macro_f1']:.4f}", flush=True)
    except (DatasetError, OSError) as exc:
        print(f"Dataset error: {exc}", file=sys.stderr)
        return 2
    best = pick_best(reports)
    best_dir = a.out / "best"
    if best_dir.exists():
        shutil.rmtree(best_dir)
    shutil.copytree(a.out / best, best_dir)
    (best_dir / "BEST_ARCH.txt").write_text(best, encoding="utf-8")
    a.results.parent.mkdir(parents=True, exist_ok=True)
    classes = json.loads((best_dir / "labels.json").read_text(encoding="utf-8"))["classes"]
    files = {}
    for arch, r in reports.items():
        fname = f"confusion_matrix_{arch}.csv"
        confusion_csv(r["results"]["test"], classes, a.results.parent / fname)
        files[arch] = fname
    thr = json.loads(a.threshold_file.read_text(encoding="utf-8")) if a.threshold_file and a.threshold_file.is_file() else None
    a.results.write_text(results_markdown(reports, best, files, thr, classes), encoding="utf-8")
    (a.out / "summary.json").write_text(json.dumps({"best": best, "val_macro_f1": {k: v["results"]["val"]["macro_f1"] for k, v in reports.items()}}, indent=2), encoding="utf-8")
    print(f"best by validation macro-F1: {best}; results written to {a.results}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
