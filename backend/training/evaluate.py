"""Evaluate a saved model on the held-out TEST split of a processed dataset. Run from backend/:

    python -m training.evaluate --manifest <manifest.csv> --model-dir models --out <report.json>

The split is recomputed exactly as at training time (same seed from metrics.json, or the manifest's predefined split), so the test
samples are the ones never used for training or model selection. Reports top-1, top-5, macro precision/recall/F1, per-class
accuracy, the confusion matrix, accuracy versus coverage at confidence thresholds, and single sequence CPU latency.
Nothing here fabricates data: if the model and dataset do not match, it stops with an error.
"""

import argparse
import json
import statistics
import sys
import time
from pathlib import Path

from app.recognition.artifacts import ModelLoadError, load_artifacts
from app.recognition.inference import SignRecognizer
from training.data import DatasetError
from training.dataset import load_splits
from training.slr_metrics import full_report
from training.train import predict_probs
from training.validate_dataset import validate


def evaluate(manifest: Path, model_dir: Path) -> dict:
    metrics_file = model_dir / "metrics.json"
    if not metrics_file.is_file():
        raise DatasetError(f"{metrics_file} not found; it records the seed used for the split")
    seed = int(json.loads(metrics_file.read_text(encoding="utf-8"))["hyperparameters"]["seed"])
    try:
        model, config = load_artifacts(model_dir)
    except ModelLoadError as exc:
        raise DatasetError(str(exc)) from exc

    validate(manifest.parent)
    data = load_splits(manifest, seed)
    test = data.stores["test"]
    unknown = sorted({s.label for s in data.samples["test"]} - set(config.classes))
    if unknown:
        raise DatasetError(f"test labels not known to the model: {unknown[:5]}")
    if data.classes != config.classes:
        raise DatasetError("the manifest's classes differ from the model's class map")

    report = full_report(predict_probs(model, test.all(config.seq_len, config.max_gap)), test.labels, config.classes)

    rec = SignRecognizer(model, config)
    times = []
    for i in range(min(len(test), 200)):
        t = time.perf_counter()
        rec.predict(test.sequences[i])
        times.append((time.perf_counter() - t) * 1000)
    times.sort()
    return {
        "architecture": config.arch,
        "split_method": data.method,
        "signer_independence_verified": data.method == "signer-disjoint",
        "test_signers": sorted({s.signer for s in data.samples["test"]}),
        "num_test_samples": len(data.samples["test"]),
        "classes_in_model": len(config.classes),
        **report,
        "inference_latency_ms_per_sequence": {
            "n": len(times), "median": round(statistics.median(times), 3), "p95": round(times[max(0, int(len(times) * 0.95) - 1)], 3),
            "note": "single CPU sequence of seq_len frames, model only (no landmark extraction)",
        },
    }


def to_markdown(r: dict) -> str:
    lines = [
        f"# Evaluation report ({r.get('architecture', 'model')})",
        f"Split: {r['split_method']} (signer independence verified: {r['signer_independence_verified']}). "
        f"Test samples: {r['num_test_samples']}; classes with test support: {r['num_classes_with_support']} of {r['classes_in_model']}.",
        "",
        f"Top-1 {r['top1_accuracy']:.4f}; top-5 {r['top5_accuracy']:.4f}; macro-precision {r['macro_precision']:.4f}; "
        f"macro-recall {r['macro_recall']:.4f}; macro-F1 {r['macro_f1']:.4f}.",
        "",
        "Accuracy versus coverage (a sample below the threshold is reported as UNRECOGNIZED):",
        "",
        "| Threshold | Coverage | Accuracy on answered | Unrecognized |",
        "|---|---|---|---|",
    ]
    for c in r["accuracy_vs_coverage"]:
        acc = "n/a" if c["accuracy_on_answered"] is None else f"{c['accuracy_on_answered']:.4f}"
        lines.append(f"| {c['threshold']:.2f} | {c['coverage']:.4f} | {acc} | {c['unrecognized']} |")
    lines += ["", "| Class | Precision | Recall | F1 | Accuracy | Support |", "|---|---|---|---|---|---|"]
    for name, c in r["per_class"].items():
        a = r["per_class_accuracy"][name]["accuracy"]
        lines.append(f"| {name} | {c['precision']:.3f} | {c['recall']:.3f} | {c['f1']:.3f} | {'n/a' if a is None else f'{a:.3f}'} | {c['support']} |")
    return "\n".join(lines) + "\n"


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--manifest", type=Path, required=True)
    p.add_argument("--model-dir", type=Path, default=Path("models"))
    p.add_argument("--out", type=Path, required=True, help="JSON report path; a .md copy is written beside it")
    a = p.parse_args()
    try:
        report = evaluate(a.manifest, a.model_dir)
    except DatasetError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    a.out.with_suffix(".md").write_text(to_markdown(report), encoding="utf-8")
    print(f"top1={report['top1_accuracy']:.4f} top5={report['top5_accuracy']:.4f} macro_f1={report['macro_f1']:.4f} n={report['num_test_samples']} ({report['split_method']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
