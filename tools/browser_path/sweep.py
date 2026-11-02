"""Validation videos: baseline per source, then how much accuracy is lost when the landmarks are perturbed, to choose augmentation ranges.
Perturbations are applied to the browser landmarks (corrected, as the app sends them). Run from backend/ with the venv."""
import json
import random
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).parent
sys.argv = [sys.argv[0]]
src = (HERE / "evaluate.py").read_text(encoding="utf-8").split("rows_out = []")[0]
exec(compile(src, "evaluate_helpers", "exec"))


def correct(o, label):
    return bool(o.get("accepted")) and o["top"].lower() == label.lower()


def run(frames_by_id, fn=None):
    n = c = w = 0
    for s in samples:
        fr = frames_by_id[s["id"]]
        if fn:
            fr = fn(fr, s["id"])
        o = classify_frames(fr)
        n += 1
        if "top" in o and o["accepted"]:
            c += correct(o, s["label"])
            w += not correct(o, s["label"])
    return round(c / n, 2), round(w / n, 2)


def noise(sigma, seed=0):
    def f(frames, sid):
        rng = np.random.default_rng(abs(hash((sid, seed))) % (2**32))
        out = []
        for fr in frames:
            def pts(p):
                return None if p is None else [q.model_copy(update={"x": q.x + rng.normal(0, sigma), "y": q.y + rng.normal(0, sigma)}) for q in p]
            out.append(LandmarkFrame(pose=pts(fr.pose), left_hand=pts(fr.left_hand), right_hand=pts(fr.right_hand)))
        return out
    return f


def drop_hands(rate, seed=0):
    def f(frames, sid):
        rng = random.Random(f"{sid}{seed}")
        return [LandmarkFrame(pose=fr.pose, left_hand=None if rng.random() < rate else fr.left_hand, right_hand=None if rng.random() < rate else fr.right_hand) for fr in frames]
    return f


br169 = {s["id"]: browser_frames("16x9", s["id"]) for s in samples}
br43 = {s["id"]: browser_frames("4x3", s["id"]) for s in samples}
res = {}
off = {"n": 0, "c": 0, "w": 0}
for s in samples:
    npy = None
    for d in ("include", "include_v2"):
        pth = ROOT / "data/processed" / d / s["npy"]
        if pth.exists():
            npy = np.load(pth)
            break
    if npy is None:
        continue
    o = classify_rows(npy.astype(np.float32))
    off["n"] += 1
    off["c"] += correct(o, s["label"])
    off["w"] += o["accepted"] and not correct(o, s["label"])
res["offline"] = (round(off["c"] / off["n"], 2), round(off["w"] / off["n"], 2), off["n"])
res["br16x9"] = run(br169)
res["br4x3"] = run(br43)
res["br4x3_raw"] = run(br43, lambda fr, sid: scale_y(fr, 0.75))
print(res, flush=True)
sweep = {}
for f in (0.6, 0.75, 0.9, 1.1, 1.25, 1.33, 1.5, 1.75):
    sweep[f"y_x{f}_on_16x9"] = run(br169, lambda fr, sid, f=f: scale_y(fr, f))
    sweep[f"y_x{f}_on_4x3"] = run(br43, lambda fr, sid, f=f: scale_y(fr, f))
    print(f, sweep[f"y_x{f}_on_16x9"], sweep[f"y_x{f}_on_4x3"], flush=True)
for sg in (0.002, 0.005, 0.01, 0.02):
    sweep[f"noise_{sg}_on_16x9"] = run(br169, noise(sg))
    print("noise", sg, sweep[f"noise_{sg}_on_16x9"], flush=True)
for rt in (0.1, 0.2, 0.4, 0.6):
    sweep[f"hand_drop_{rt}_on_16x9"] = run(br169, drop_hands(rt))
    print("hand drop", rt, sweep[f"hand_drop_{rt}_on_16x9"], flush=True)
json.dump({"baseline": res, "sweep": sweep}, open(HERE / "sweep.json", "w"), indent=1)
