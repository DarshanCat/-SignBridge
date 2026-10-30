"""Pilot training runs to debug the pipeline and compare settings. Run from backend/:

    python -m training.pilot --manifest ..\\data\\processed\\include\\manifest.csv --out ..\\docs\\evaluation\\pilot ^
        --models-dir ..\\data\\pilot_models --runs cnn1d:cnn1d bigru:bigru transformer:transformer

Each run is  <name>:<arch>[:key=value,...]  (keys: epochs, lr, hidden, layers, dropout, batch_size, augment, class_weights, max_gap, seed).

Pilot rules: the TEST split is never read (no feature file of the test split is opened); model selection and the reported numbers use the
validation split only. Every result file is labelled "pilot, v1 partial split, not reportable". Existing result files are never overwritten.
"""

import argparse
import json
import sys
import time
from pathlib import Path

from training.data import DatasetError
from training.train import train

LABEL = "pilot, v1 partial split, not reportable"
INT_KEYS = {"epochs", "hidden", "layers", "batch_size", "max_gap", "seed", "patience", "seq_len", "heads"}
FLOAT_KEYS = {"lr", "dropout", "noise_std"}
BOOL_KEYS = {"augment", "class_weights"}


def parse_run(spec: str) -> tuple[str, str, dict]:
    parts = spec.split(":")
    if len(parts) < 2 or not parts[0] or not parts[1]:
        raise ValueError(f"bad run spec {spec!r}; expected name:arch[:key=value,...]")
    kw: dict = {}
    if len(parts) > 2 and parts[2]:
        for item in parts[2].split(","):
            k, _, v = item.partition("=")
            if k in INT_KEYS:
                kw[k] = int(v)
            elif k in FLOAT_KEYS:
                kw[k] = float(v)
            elif k in BOOL_KEYS:
                kw[k] = v.lower() in {"1", "true", "yes"}
            else:
                raise ValueError(f"unknown hyperparameter {k!r} in {spec!r}")
    return parts[0], parts[1], kw


def summarize(report: dict, name: str, arch: str, seconds: float) -> dict:
    v = report["results"]["val"]
    assert "test" not in report["results"], "pilot runs must not evaluate the test split"
    return {
        "label": LABEL,
        "run": name,
        "arch": arch,
        "validation": {
            "top1_accuracy": v["top1_accuracy"], "top5_accuracy": v["top5_accuracy"], "macro_f1": v["macro_f1"], "num_samples": v["num_samples"],
        },
        "test_split_evaluated": False,
        "hyperparameters": report["hyperparameters"],
        "parameters": report["parameters"],
        "epochs_run": report["hyperparameters"]["epochs_run"],
        "seconds": round(seconds, 1),
        "split_method": report["split_method"],
        "sample_counts": {k: n for k, n in report["sample_counts"].items() if k != "test"},
        "classes_missing_from_train": report["classes_missing_from_train"],
        "note": "Authors' predefined INCLUDE split on the partial v1 data; signer independence unverified. Not a reportable result.",
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--manifest", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True, help="result folder (docs/evaluation/pilot)")
    p.add_argument("--models-dir", type=Path, required=True, help="where pilot weights go (not under docs)")
    p.add_argument("--runs", nargs="+", required=True)
    p.add_argument("--threads", type=int, default=2)
    a = p.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    rows = []
    for spec in a.runs:
        try:
            name, arch, kw = parse_run(spec)
        except ValueError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 2
        target = a.out / f"{name}.json"
        if target.exists():
            print(f"Error: {target} exists; pilot results are never overwritten (choose another run name)", file=sys.stderr)
            return 2
        t0 = time.time()
        try:
            report = train(a.manifest, a.models_dir / name, arch=arch, num_threads=a.threads, evaluate_test=False, **kw)
        except DatasetError as exc:
            print(f"Dataset error: {exc}", file=sys.stderr)
            return 2
        row = summarize(report, name, arch, time.time() - t0)
        target.write_text(json.dumps(row, indent=2), encoding="utf-8")
        rows.append(row)
        v = row["validation"]
        print(f"[{LABEL}] {name} ({arch}): val top1={v['top1_accuracy']:.3f} top5={v['top5_accuracy']:.3f} macroF1={v['macro_f1']:.3f} "
              f"epochs={row['epochs_run']} {row['seconds']}s", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
