"""Timings for the estimate of a pixel based sign model (a pretrained image encoder per frame, then a recurrent model): this machine's speed for video decoding and for
several image encoders. The encoders are the torchvision architectures with random weights: the time of a forward pass does not depend on the weights, and nothing is
downloaded. Nothing is trained and no INCLUDE sign model is touched. Needs torch, torchvision and opencv (a scratch environment is fine).
usage: python measure.py <one INCLUDE video file> <out.json>"""
import json
import os
import platform
import statistics as st
import sys
import time

import cv2
import torch
import torchvision

video, out = sys.argv[1], sys.argv[2]
res = {"machine": {"cpu_count": os.cpu_count(), "platform": platform.platform(), "torch": torch.__version__, "torchvision": torchvision.__version__}}

# decoding: every frame of one real INCLUDE video, resized to 224 x 224 like an encoder input
cap = cv2.VideoCapture(video)
w, h, fps, n = int(cap.get(3)), int(cap.get(4)), cap.get(5), int(cap.get(7))
cv2.setNumThreads(1)
t0 = time.perf_counter()
frames = 0
while True:
    ok, f = cap.read()
    if not ok:
        break
    cv2.resize(f, (224, 224))
    frames += 1
dt = time.perf_counter() - t0
res["decode"] = {"video": os.path.basename(video), "width": w, "height": h, "fps": fps, "frames": frames, "ms_per_frame_single_thread": round(1000 * dt / frames, 2)}

# encoders: forward pass of a batch of 32 frames at 224 x 224 (and a 112 x 112 variant), no gradients, then forward + backward for fine tuning
def bench(model, size, threads, batch=32, reps=4, train=False):
    torch.set_num_threads(threads)
    x = torch.randn(batch, 3, size, size)
    model.train(train)
    ctx = torch.enable_grad() if train else torch.no_grad()
    with ctx:
        for _ in range(2):  # warm up
            y = model(x)
            if train:
                y.sum().backward()
        ts = []
        for _ in range(reps):
            t = time.perf_counter()
            y = model(x)
            if train:
                y.sum().backward()
            ts.append(time.perf_counter() - t)
    return round(1000 * st.median(ts) / batch, 2)  # ms per frame


models = {
    "mobilenet_v3_small": torchvision.models.mobilenet_v3_small,
    "mobilenet_v3_large": torchvision.models.mobilenet_v3_large,
    "resnet18": torchvision.models.resnet18,
    "efficientnet_b0": torchvision.models.efficientnet_b0,
    "resnet50": torchvision.models.resnet50,
}
res["encoders"] = {}
for name, ctor in models.items():
    m = ctor(weights=None)
    res["encoders"][name] = {
        "parameters": sum(p.numel() for p in m.parameters()),
        "ms_per_frame_224_forward_all_threads": bench(m, 224, os.cpu_count()),
        "ms_per_frame_224_forward_4_threads": bench(m, 224, 4),
        "ms_per_frame_112_forward_all_threads": bench(m, 112, os.cpu_count()),
        "ms_per_frame_224_forward_backward_all_threads": bench(m, 224, os.cpu_count(), batch=16, reps=3, train=True) if name in ("mobilenet_v3_small", "resnet18") else None,
    }
    print(name, res["encoders"][name], flush=True)
with open(out, "w", encoding="utf-8") as f:
    json.dump(res, f, indent=1)
