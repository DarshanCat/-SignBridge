"""Throughput of several encoder processes at once (4 processes with 4 threads each, forward pass of 32 frames at 224 x 224, random weights), to see whether
running workers side by side beats one process with all threads. usage: python parallel.py <timing.json to extend>"""
import json
import multiprocessing as mp
import sys
import time

import torch
import torchvision


def work(args):
    name, threads, seconds = args
    torch.set_num_threads(threads)
    m = getattr(torchvision.models, name)(weights=None).eval()
    x = torch.randn(32, 3, 224, 224)
    frames, t0 = 0, None
    with torch.no_grad():
        m(x)  # warm up
        t0 = time.perf_counter()
        while time.perf_counter() - t0 < seconds:
            m(x)
            frames += 32
    return frames / (time.perf_counter() - t0)


if __name__ == "__main__":
    path = sys.argv[1]
    d = json.load(open(path, encoding="utf-8"))
    d["parallel_4_processes_x_4_threads_frames_per_second"] = {}
    for name in ("mobilenet_v3_small", "resnet18", "efficientnet_b0"):
        with mp.Pool(4) as p:
            fps = sum(p.map(work, [(name, 4, 12)] * 4))
        single = 1000 / d["encoders"][name]["ms_per_frame_224_forward_all_threads"]
        d["parallel_4_processes_x_4_threads_frames_per_second"][name] = {"parallel": round(fps, 1), "single_process_all_threads": round(single, 1)}
        print(name, d["parallel_4_processes_x_4_threads_frames_per_second"][name], flush=True)
    json.dump(d, open(path, "w", encoding="utf-8"), indent=1)
