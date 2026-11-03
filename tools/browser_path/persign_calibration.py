"""Per-sign loss from 16:9 to 4:3 and calibration of the baseline CNN, VALIDATION corpus (211 videos) only; no test video is used.

Inputs (all written earlier, nothing is re-run): docs/evaluation/eval_val.json (seed 0), eval_val_s1.json and eval_val_s2.json (base_cnn, browser landmarks,
conditions offline / br16x9 / br4x3 / br4x3_raw as [correct, top-1 confidence] per video or null) and the stored features of the same videos.
usage (repository root):  python -I tools/browser_path/persign_calibration.py
Writes docs/evaluation/persign_calibration_val.json and prints the numbers used in the paper."""
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
EV = ROOT / "docs" / "evaluation"
TAU = 0.7
FILES = {0: EV / "eval_val.json", 1: EV / "eval_val_s1.json", 2: EV / "eval_val_s2.json"}
samples = json.load(open(EV / "browser_corpus_val_samples.json"))["samples"]
data = {s: json.load(open(f)) for s, f in FILES.items()}
n = len(samples)
assert all(d["n"] == n for d in data.values())


def ok(r):
    return r is not None and r[1] >= TAU and bool(r[0])


# ---------------------------------------------------------------- vertical hand movement range from the stored features
def hand_range(npy):
    a = np.load(ROOT / "data" / "processed" / "include" / npy) if (ROOT / "data" / "processed" / "include" / npy).is_file() else np.load(ROOT / "data" / "processed" / "include_v2" / npy)
    a = a.reshape(a.shape[0], 75, 3)
    best = 0.0
    for first in (33, 54):  # left hand, right hand (21 points each): wrist y, in shoulder widths
        y = a[:, first, 1]
        present = np.abs(a[:, first:first + 21, :]).sum(axis=(1, 2)) > 0
        if present.sum() >= 3:
            best = max(best, float(np.percentile(y[present], 95) - np.percentile(y[present], 5)))
    return best


rng_hand = np.array([hand_range(s["npy"]) for s in samples])

# ---------------------------------------------------------------- per video and per sign loss (base CNN, three seeds)
ok16 = np.array([[ok(data[s]["conditions"]["br16x9"]["base_cnn"][i]) for i in range(n)] for s in data], dtype=float)  # seeds x videos
ok43 = np.array([[ok(data[s]["conditions"]["br4x3"]["base_cnn"][i]) for i in range(n)] for s in data], dtype=float)
loss = ok16 - ok43                       # +1 lost, -1 gained
vloss = loss.mean(axis=0)                # per video, mean over the three seeds
labels = np.array([s["label"] for s in samples])
per_sign = {}
for lab in sorted(set(labels)):
    idx = np.where(labels == lab)[0]
    per_sign[lab] = {"videos": int(len(idx)), "lost": int((loss[:, idx] > 0).sum()), "gained": int((loss[:, idx] < 0).sum()),
                     "ok16_total": int(ok16[:, idx].sum()), "range": float(np.mean(rng_hand[idx]))}
ranked = sorted(per_sign.items(), key=lambda kv: (-(kv[1]["lost"] - kv[1]["gained"]), -kv[1]["lost"], kv[0]))
top = [(k, v) for k, v in ranked if v["lost"] - v["gained"] > 0][:12]


def spearman(x, y):
    def rank(v):
        o = np.argsort(v, kind="mergesort")
        r = np.empty(len(v))
        r[o] = np.arange(len(v))
        for u in np.unique(v):
            m = v == u
            r[m] = r[m].mean()
        return r
    rx, ry = rank(np.asarray(x, float)), rank(np.asarray(y, float))
    return float(np.corrcoef(rx, ry)[0, 1])


def perm_p(x, y, reps=20000, seed=0):
    rng = np.random.default_rng(seed)
    obs = spearman(x, y)
    cnt = sum(1 for _ in range(reps) if abs(spearman(x, rng.permutation(y))) >= abs(obs))
    return obs, (cnt + 1) / (reps + 1)


rho_all, p_all = perm_p(vloss, rng_hand)
at_risk = ok16.mean(axis=0) > 0          # videos that the model answers correctly in 16:9 in at least one seed
rho_risk, p_risk = perm_p(vloss[at_risk], rng_hand[at_risk])
lost_any = (loss > 0).any(axis=0)
med_lost = float(np.median(rng_hand[at_risk & lost_any]))
med_kept = float(np.median(rng_hand[at_risk & ~lost_any]))

# ---------------------------------------------------------------- calibration (expected calibration error, 10 equal-width bins)
def ece(res, bins=10):
    pairs = [(r[1], bool(r[0])) for r in res if r is not None]
    conf = np.array([p[0] for p in pairs])
    cor = np.array([p[1] for p in pairs], dtype=float)
    edges = np.linspace(0, 1, bins + 1)
    e = 0.0
    for lo, hi in zip(edges[:-1], edges[1:]):
        m = (conf > lo) & (conf <= hi) if lo > 0 else (conf >= lo) & (conf <= hi)
        if m.any():
            e += m.mean() * abs(cor[m].mean() - conf[m].mean())
    return float(e), float(conf.mean()), float(cor.mean()), len(pairs)


cal = {}
for c in ("offline", "br16x9", "br4x3", "br4x3_raw"):
    vals = [ece(data[s]["conditions"][c]["base_cnn"]) for s in data]
    cal[c] = {"ece_per_seed": [v[0] for v in vals], "mean_conf_per_seed": [v[1] for v in vals], "top1_per_seed": [v[2] for v in vals], "n_per_seed": [v[3] for v in vals]}

out = {"n_videos": n, "tau": TAU, "classes": len(per_sign),
       "top_signs": [{"sign": k, **v} for k, v in top],
       "spearman_all": {"rho": rho_all, "p": p_all, "n": n},
       "spearman_at_risk": {"rho": rho_risk, "p": p_risk, "n": int(at_risk.sum())},
       "median_range_lost_any": med_lost, "median_range_not_lost": med_kept, "n_lost_any": int((at_risk & lost_any).sum()), "n_not_lost": int((at_risk & ~lost_any).sum()),
       "totals": {"lost": int((loss > 0).sum()), "gained": int((loss < 0).sum()), "pairs": int(loss.size)},
       "calibration": cal}
json.dump(out, open(EV / "persign_calibration_val.json", "w"), indent=1)
print(json.dumps({k: v for k, v in out.items() if k != "calibration"}, indent=1))
for c, v in cal.items():
    print(c, "ECE", [round(x, 3) for x in v["ece_per_seed"]], "conf", [round(x, 2) for x in v["mean_conf_per_seed"]], "top1", [round(x, 2) for x in v["top1_per_seed"]], "n", v["n_per_seed"])
