"""Does accuracy drop when validation sequences are sampled at the live frame rate instead of the training rate? VALIDATION split only (the test split is never read), no retraining,
the existing baseline CNNs (seeds 0, 1, 2; no face), their own threshold-free macro-F1.
Training rate: INCLUDE videos are 25 fps (30 videos sampled from the archives on disk, all 25.0) and the features keep every second frame, so 12.5 frames per second.
A lower rate is simulated by keeping, from each sequence, the frames nearest to the times k / rate; the model's own preprocessing (gap fill, resample to 32 frames) then runs as in
training and live use. Three sampling phases (the first kept frame at 0, 1/3 and 2/3 of a step) are averaged, so no result depends on one lucky phase.
usage (from backend/): python ..\\tools\\fps_effect\\validation_rate.py"""
import json
import math
import statistics as st
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
from app.recognition.artifacts import load_artifacts  # noqa: E402
from app.recognition.preprocess import prepare_sequence_full  # noqa: E402
from training.augment import thin_to_rate  # noqa: E402
from training.dataset import load_splits  # noqa: E402
from training.slr_metrics import full_report  # noqa: E402
from training.train import predict_probs  # noqa: E402

TRAIN_FPS = 12.5
RATES = [12.5, 8.0, 6.7]  # training rate, GPU-delegate extraction rate (extra row), live CPU-delegate rate (docs/evaluation/LATENCY.md)
PHASES = [0.0, 1 / 3, 2 / 3]
SEEDS = {0: ROOT / "data" / "models_v2" / "cnn", 1: ROOT / "data" / "models_seeds" / "s1_base" / "cnn", 2: ROOT / "data" / "models_seeds" / "s2_base" / "cnn"}
T95 = 4.303
MANIFEST = ROOT / "data" / "processed" / "include_v2" / "manifest.csv"


sample_at = thin_to_rate  # the same function the frame rate augmentation of training uses


def macro_f1(model, cfg, store, rate: float, phase: float) -> tuple[float, float]:
    x = np.stack([prepare_sequence_full(sample_at(s, rate, phase), cfg.seq_len, cfg.max_gap) for s in store.sequences])
    rep = full_report(predict_probs(model, x), store.labels, cfg.classes)
    return rep["macro_f1"], rep["top1_accuracy"]


def main() -> None:
    out = {"train_fps_assumed": TRAIN_FPS, "rates": RATES, "phases": PHASES, "per_seed": {}, "note": "validation split only; the test split was not read"}
    for seed, d in SEEDS.items():
        model, cfg = load_artifacts(d)
        model.eval()
        recorded = json.loads((d / "metrics.json").read_text(encoding="utf-8"))["results"]["val"]["macro_f1"]
        split_seed = int(json.loads((d / "metrics.json").read_text(encoding="utf-8"))["hyperparameters"]["seed"])
        store = load_splits(MANIFEST, split_seed, load_test=False).stores["val"]  # predefined split: the same 347 validation sequences for every seed
        row = {"recorded_val_macro_f1": recorded, "validation_sequences": len(store), "median_frames_at_12_5_fps": int(st.median(len(s) for s in store.sequences))}
        for rate in RATES:
            res = [macro_f1(model, cfg, store, rate, p) for p in (PHASES if rate < TRAIN_FPS else [0.0])]
            row[str(rate)] = {"macro_f1": st.mean(r[0] for r in res), "macro_f1_by_phase": [r[0] for r in res], "top1": st.mean(r[1] for r in res),
                              "median_frames_kept": int(st.median(len(sample_at(s, rate, 0.0)) for s in store.sequences))}
        out["per_seed"][str(seed)] = row
        print(seed, {k: (round(v["macro_f1"], 4) if isinstance(v, dict) else v) for k, v in row.items()}, flush=True)
    summary = {}
    for rate in RATES[1:]:
        d = [out["per_seed"][str(s)][str(rate)]["macro_f1"] - out["per_seed"][str(s)][str(TRAIN_FPS)]["macro_f1"] for s in SEEDS]
        m, sd = st.mean(d), st.stdev(d)
        half = T95 * sd / math.sqrt(len(d))
        summary[str(rate)] = {"per_seed_difference": d, "mean_difference": m, "lo": m - half, "hi": m + half, "clear": not (m - half <= 0 <= m + half)}
    out["difference_vs_training_rate"] = summary
    (ROOT / "docs" / "evaluation" / "fps_effect.json").write_text(json.dumps(out, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
