"""Cost of one training epoch of the project's sequence models when the input per frame is an image embedding instead of the 225 landmark features: random data of the real
shape (3121 training sequences, 32 frames, batch 16, Adam), the real model classes (app.recognition.models, 262 classes), 10 torch threads as in training.
usage (from backend/): python ..\tools\pixel_estimate\sequence_cost.py <timing.json to extend>"""
import json
import sys
import time

import torch
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))
from torch import nn

from app.recognition.artifacts import ModelConfig
from app.recognition.models import build_model

torch.set_num_threads(10)
path = sys.argv[1]
d = json.load(open(path, encoding="utf-8"))
d["sequence_epoch_seconds"] = {}
for arch in ("cnn", "bigru"):
    for dim in (225, 576):
        m = build_model(ModelConfig([f"c{i}" for i in range(262)], dim, 32, 128, 2, 0.3, arch, 4, 3))
        opt = torch.optim.Adam(m.parameters(), 1e-3)
        x = torch.randn(16, 32, dim)
        y = torch.randint(0, 262, (16,))
        for _ in range(3):  # warm up
            nn.functional.cross_entropy(m(x), y).backward()
        t0 = time.perf_counter()
        for _ in range(195):  # 3121 sequences at batch 16
            opt.zero_grad()
            nn.functional.cross_entropy(m(x), y).backward()
            opt.step()
        d["sequence_epoch_seconds"][f"{arch}_{dim}"] = round(time.perf_counter() - t0, 1)
        print(arch, dim, d["sequence_epoch_seconds"][f"{arch}_{dim}"], flush=True)
json.dump(d, open(path, "w", encoding="utf-8"), indent=1)
