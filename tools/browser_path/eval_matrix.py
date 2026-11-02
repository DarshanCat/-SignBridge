"""Evaluate baseline and augmented CNN, BiGRU and Transformer on the browser-path corpora, with perturbation sweeps and framing.

usage (from backend/ with the venv):  python eval_matrix.py val|test <models_base_dir> <models_aug_dir> <out.json>
val  : browser 16:9, browser 4:3 (rescaled and raw), offline features, y scale, noise, hand dropout sweeps, framing (shrunk) frames.
test : browser 16:9, browser 4:3 (rescaled and raw), offline features only. Run once per final model.
"""
import json
import random
import sys
from pathlib import Path

import numpy as np

BACKEND = Path(r"C:\Users\Darshan\Downloads\MONEY Bank\3d project\backend")
sys.path.insert(0, str(BACKEND))
HERE = Path(__file__).parent
ROOT = BACKEND.parent

from app.recognition.inference import get_recognizer  # noqa: E402
from app.recognition.landmarks import process_sequence  # noqa: E402
from app.schemas.landmarks import LandmarkFrame, LandmarkSequenceRequest  # noqa: E402

split, base_dir, aug_dir, out_path = sys.argv[1], Path(sys.argv[2]), Path(sys.argv[3]), Path(sys.argv[4])
ARCHS = ["cnn", "bigru", "transformer"]
THRESHOLDS = [0.0, 0.3, 0.5, 0.7, 0.8, 0.9, 0.95]
CORPUS = HERE / split
samples = json.load(open(CORPUS / "samples.json"))["samples"]
labels = [s["label"] for s in samples]
MODELS = {f"{kind}_{a}": get_recognizer(d / a) for kind, d in (("base", base_dir), ("aug", aug_dir)) for a in ARCHS}


def buffer_frames(frames):
    buf, miss = [], 0
    for f in frames:
        miss = 0 if f.pose else miss + 1
        if miss > 15:
            buf = []
            continue
        buf = (buf + [f])[-60:]
    return buf


def rows_of(frames):
    buf = buffer_frames(frames)
    if not buf:
        return None
    proc = process_sequence(LandmarkSequenceRequest(frames=buf))
    if not proc.usable:
        return None
    return np.array([f for f, r in zip(proc.features, proc.frame_reports) if r.valid], dtype=np.float32)


def scale_y(frames, k):
    def pts(p):
        return None if p is None else [q.model_copy(update={"y": q.y * k}) for q in p]

    return [LandmarkFrame(pose=pts(f.pose), left_hand=pts(f.left_hand), right_hand=pts(f.right_hand)) for f in frames]


def add_noise(frames, sigma, key):
    rng = np.random.default_rng(abs(hash(("n", key))) % (2**32))

    def pts(p):
        return None if p is None else [q.model_copy(update={"x": q.x + rng.normal(0, sigma), "y": q.y + rng.normal(0, sigma)}) for q in p]

    return [LandmarkFrame(pose=pts(f.pose), left_hand=pts(f.left_hand), right_hand=pts(f.right_hand)) for f in frames]


def drop_hands(frames, rate, key):
    rng = random.Random(f"d{key}")
    return [LandmarkFrame(pose=f.pose, left_hand=None if rng.random() < rate else f.left_hand, right_hand=None if rng.random() < rate else f.right_hand) for f in frames]


def browser(framing):
    return [[LandmarkFrame.model_validate(f) for f in json.load(open(CORPUS / "browser" / framing / f"{s['id']}.json"))["frames"]] for s in samples]


def predict_all(rows_list):
    """{model: [(top label, confidence) or None per video]}"""
    out = {}
    for name, rec in MODELS.items():
        res = []
        for rows in rows_list:
            if rows is None or len(rows) == 0:
                res.append(None)
            else:
                p = rec.predict(rows, top_k=1)[0]
                res.append((p.label, p.confidence))
        out[name] = res
    return out


def summarize(preds, labs, tau=0.7):
    r = {}
    for name, res in preds.items():
        c = w = u = n0 = t1 = 0
        for p, lab in zip(res, labs):
            if p is None:
                n0 += 1
                continue
            hit = p[0].lower() == lab.lower()
            t1 += hit
            if p[1] >= tau:
                c += hit
                w += not hit
            else:
                u += 1
        r[name] = {"n": len(labs), "correct": c, "wrong": w, "unrec": u, "no_result": n0, "top1": t1}
    return r


def dump(preds, labs):
    """raw per video results so the report can recompute thresholds, intervals and paired tests"""
    return {name: [None if p is None else [p[0].lower() == lab.lower(), round(p[1], 5)] for p, lab in zip(res, labs)] for name, res in preds.items()}


result = {"split": split, "n": len(samples), "conditions": {}}


def cond(name, rows_list, labs=None):
    preds = predict_all(rows_list)
    result["conditions"][name] = dump(preds, labs or labels)
    s = summarize(preds, labs or labels)
    print(name, {k: (v["correct"], v["wrong"], v["unrec"]) for k, v in s.items()}, flush=True)


# offline features of the same videos (stride 1, 1080p): the normal evaluation path
off = []
for s in samples:
    arr = None
    for d in ("include", "include_v2"):
        p = ROOT / "data/processed" / d / s["npy"]
        if p.exists():
            arr = np.load(p).astype(np.float32)
            break
    off.append(arr)
cond("offline", off)

b169, b43 = browser("16x9"), browser("4x3")
cond("br16x9", [rows_of(f) for f in b169])
cond("br4x3", [rows_of(f) for f in b43])
cond("br4x3_raw", [rows_of(scale_y(f, 0.75)) for f in b43])
json.dump(result, open(out_path, "w"))

LIGHT = len(sys.argv) > 5  # extra seeds: the four main conditions only, no sweeps
if split == "val" and not LIGHT:
    for k in (0.75, 0.9, 1.1, 1.25, 1.5):
        cond(f"y_{k}", [rows_of(scale_y(f, k)) for f in b169])
    for sg in (0.005, 0.01, 0.02):
        cond(f"noise_{sg}", [rows_of(add_noise(f, sg, i)) for i, f in enumerate(b169)])
    for rt in (0.2, 0.4, 0.6):
        cond(f"drop_{rt}", [rows_of(drop_hands(f, rt, i)) for i, f in enumerate(b169)])
    json.dump(result, open(out_path, "w"))
    # framing: Python landmarks of shrunk frames (first 60 videos of the 100-video validation list, see zoom_save.py)
    zdir = HERE / "zoom"
    for fac in (1.0, 0.8, 0.6, 0.45):
        files = sorted(zdir.glob(f"*_{fac}.json"))
        rows_list, labs, widths = [], [], []
        for fpath in files:
            d = json.load(open(fpath))
            frames = [LandmarkFrame.model_validate(f) for f in d["frames"]]
            w = [abs(f.pose[11].x - f.pose[12].x) for f in frames if f.pose]
            widths.append(float(np.median(w)) if w else 0.0)
            rows_list.append(rows_of(frames))
            labs.append(d["label"])
        preds = predict_all(rows_list)
        result["conditions"][f"zoom_{fac}"] = dump(preds, labs)
        result["conditions"][f"zoom_{fac}_width"] = widths
        s = summarize(preds, labs)
        print("zoom", fac, len(labs), {k: (v["correct"], v["wrong"], v["unrec"]) for k, v in s.items()}, flush=True)
    json.dump(result, open(out_path, "w"))
print("done", flush=True)
