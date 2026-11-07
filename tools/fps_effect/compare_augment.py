"""CNN trained with frame rate augmentation (data/models_fps) against the baseline CNN (no augmentation), validation macro-F1 at 12.5, 8 and 6.7 fps, seeds 0, 1, 2.
VALIDATION split only, no test split, no retraining here. Uses the same thinning function and the same three sampling phases as tools/fps_effect/validation_rate.py.
usage (from backend/): python ..\tools\fps_effect\compare_augment.py   then (repository root) python -I tools/fps_effect/compare_augment_report.py"""
import json
import math
import statistics as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import validation_rate as vr  # noqa: E402

ROOT = vr.ROOT
AUG = {s: ROOT / "data" / "models_fps" / f"s{s}" / "cnn" for s in (0, 1, 2)}


def evaluate(dirs):
    out = {}
    for seed, d in dirs.items():
        model, cfg = vr.load_artifacts(d)
        model.eval()
        meta = json.loads((d / "metrics.json").read_text(encoding="utf-8"))
        store = vr.load_splits(vr.MANIFEST, int(meta["hyperparameters"]["seed"]), load_test=False).stores["val"]
        row = {"recorded_val_macro_f1": meta["results"]["val"]["macro_f1"], "epochs_run": meta["hyperparameters"]["epochs_run"], "fps_augment": meta["hyperparameters"].get("fps_augment")}
        for rate in vr.RATES:
            res = [vr.macro_f1(model, cfg, store, rate, p) for p in (vr.PHASES if rate < vr.TRAIN_FPS else [0.0])]
            row[str(rate)] = {"macro_f1": st.mean(r[0] for r in res), "by_phase": [r[0] for r in res], "top1": st.mean(r[1] for r in res)}
        out[str(seed)] = row
        print(seed, {k: round(v["macro_f1"], 4) for k, v in row.items() if isinstance(v, dict)}, flush=True)
    return out


def delta(a, b):
    d = [y - x for x, y in zip(a, b)]
    m, sd = st.mean(d), st.stdev(d)
    half = vr.T95 * sd / math.sqrt(len(d))
    return {"per_seed": d, "mean": m, "lo": m - half, "hi": m + half, "clear": not (m - half <= 0 <= m + half)}


def main():
    base = evaluate(vr.SEEDS)
    aug = evaluate(AUG)
    res = {"baseline": base, "fps_augment": aug, "rates": vr.RATES, "note": "validation split only; the test split was not read", "difference": {}}
    for r in map(str, vr.RATES):
        res["difference"][r] = delta([base[s][r]["macro_f1"] for s in "012"], [aug[s][r]["macro_f1"] for s in "012"])
    res["difference"]["augmented_own_12.5_vs_baseline_12.5"] = res["difference"]["12.5"]
    (ROOT / "docs" / "evaluation" / "fps_augment_results.json").write_text(json.dumps(res, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
