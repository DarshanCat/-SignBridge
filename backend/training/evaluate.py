"""Evaluate a saved model on the held-out TEST split of a processed dataset. Run from backend/:

    python -m training.evaluate --manifest <manifest.csv> --model-dir models --out <report.json>

The split is recomputed exactly as at training time (same seed from metrics.json, or the manifest's predefined split), so
the test samples are the ones never used for training or model selection. Also times single-sample inference.
Nothing here fabricates data: if the model and dataset do not match, it stops with an error.
"""

import argparse
import json
import statistics
import sys
import time
from pathlib import Path

import numpy as np

from app.recognition.artifacts import ModelLoadError, load_artifacts
from app.recognition.inference import SignRecognizer
from training.data import DatasetError, load_arrays, read_manifest, split_samples
from training.metrics import classification_report
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
    samples = read_manifest(manifest)
    splits, method = split_samples(samples, seed)
    test = splits["test"]
    unknown = sorted({s.label for s in test} - set(config.classes))
    if unknown:
        raise DatasetError(f"test labels not known to the model: {unknown[:5]}")
    x, y = load_arrays(test, config.classes, config.seq_len)

    with np.errstate(all="ignore"):
        import torch

        with torch.no_grad():
            pred = model(torch.from_numpy(x)).argmax(dim=-1).numpy()
    report = classification_report(y, pred, config.classes)

    rec = SignRecognizer(model, config)
    times = []
    for i in range(min(len(x), 200)):
        t = time.perf_counter()
        rec.predict(x[i])
        times.append((time.perf_counter() - t) * 1000)
    times.sort()
    return {
        "split_method": method,
        "signer_independence_verified": method == "signer-disjoint",
        "test_signers": sorted({s.signer for s in test}),
        "num_test_samples": len(test),
        "classes_in_model": len(config.classes),
        **report,
        "inference_latency_ms_per_sequence": {
            "n": len(times), "median": round(statistics.median(times), 3), "p95": round(times[int(len(times) * 0.95) - 1], 3),
            "note": "single CPU sequence of seq_len frames, model only (no landmark extraction)",
        },
    }


def to_markdown(r: dict) -> str:
    lines = [
        "# Evaluation report",
        f"Split: {r['split_method']} (signer independence verified: {r['signer_independence_verified']}). "
        f"Test samples: {r['num_test_samples']}; classes with test support: {r['num_classes_with_support']} of {r['classes_in_model']}.",
        "",
        f"Accuracy {r['accuracy']:.4f}; macro-precision {r['macro_precision']:.4f}; macro-recall {r['macro_recall']:.4f}; "
        f"macro-F1 {r['macro_f1']:.4f}.",
        "",
        "| Class | Precision | Recall | F1 | Support |",
        "|---|---|---|---|---|",
    ]
    for name, c in r["per_class"].items():
        lines.append(f"| {name} | {c['precision']:.3f} | {c['recall']:.3f} | {c['f1']:.3f} | {c['support']} |")
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
    print(f"accuracy={report['accuracy']:.4f} macro_f1={report['macro_f1']:.4f} n={report['num_test_samples']} ({report['split_method']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
