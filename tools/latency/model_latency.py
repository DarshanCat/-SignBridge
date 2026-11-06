"""Model side latency of the live recognizer: preprocessing and model inference per sequence on this CPU, on the 347 VALIDATION sequences (the test split is not read).
usage (repository root):  backend\.venv\Scripts\python tools\latency\model_latency.py <out.json>   (run from backend/ so that the app package imports)"""
import json
import platform
import statistics as st
import sys
import time
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
from app.recognition.artifacts import load_artifacts  # noqa: E402
from app.recognition.inference import SignRecognizer  # noqa: E402
from app.recognition.preprocess import prepare_sequence_full  # noqa: E402
from training.dataset import load_splits  # noqa: E402


def stat(a):
    a = sorted(a)
    return {"n": len(a), "median": round(st.median(a), 3), "p95": round(a[int(0.95 * len(a)) - 1], 3), "mean": round(st.mean(a), 3), "max": round(a[-1], 3)}


model, cfg = load_artifacts(ROOT / "backend" / "models")
rec = SignRecognizer(model.eval(), cfg)
data = load_splits(ROOT / "data" / "processed" / "include_v2" / "manifest.csv", 0, load_test=False)  # validation and train only
seqs = data.stores["val"].sequences
for s in seqs[:20]:  # warm up
    rec.predict(s)
pre, fwd, total = [], [], []
for s in seqs:
    t0 = time.perf_counter()
    x = torch.from_numpy(prepare_sequence_full(s, cfg.seq_len, cfg.max_gap)).unsqueeze(0)
    t1 = time.perf_counter()
    with torch.no_grad():
        torch.softmax(model(x), dim=-1)
    t2 = time.perf_counter()
    pre.append((t1 - t0) * 1000); fwd.append((t2 - t1) * 1000)
    t3 = time.perf_counter(); rec.predict(s); total.append((time.perf_counter() - t3) * 1000)
res = {
    "model": {"arch": cfg.arch, "classes": len(cfg.classes), "seq_len": cfg.seq_len, "parameters": int(sum(p.numel() for p in model.parameters()))},
    "validation_sequences": len(seqs), "frames_per_sequence_median": int(st.median(len(s) for s in seqs)),
    "preprocess_ms": stat(pre), "model_forward_ms": stat(fwd), "predict_total_ms": stat(total),
    "torch_threads": torch.get_num_threads(), "python": platform.python_version(), "torch": torch.__version__,
    "note": "single sequence, batch 1, CPU, validation split only",
}
Path(sys.argv[1]).write_text(json.dumps(res, indent=1), encoding="utf-8")
print(json.dumps(res, indent=1))
