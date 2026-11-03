"""Paired statistics of the padding test (docs/evaluation/padding_test_val.json, 100 validation videos, baseline CNN, threshold 0.7).
usage (repository root):  python -I tools/browser_path/padding_stats.py    Writes docs/evaluation/padding_test_val.md"""
import json
import math
from math import comb
from pathlib import Path

EV = Path(__file__).resolve().parents[2] / "docs" / "evaluation"
d = json.load(open(EV / "padding_test_val.json"))
TAU = d["tau"]
C = d["conditions"]


def ok(r):
    return r["conf"] >= TAU and r["correct"]


def wilson(k, n, z=1.96):
    p = k / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return c - h, c + h


def mcnemar(a, b):
    x = sum(1 for p, q in zip(C[a]["rows"], C[b]["rows"]) if ok(p) and not ok(q))  # a right, b wrong
    y = sum(1 for p, q in zip(C[a]["rows"], C[b]["rows"]) if not ok(p) and ok(q))
    n = x + y
    if n == 0:
        return x, y, 1.0
    k = min(x, y)
    return x, y, min(1.0, 2 * sum(comb(n, i) for i in range(k + 1)) / 2**n)


out = ["# Padding test (validation, 100 videos)\n",
       "Python MediaPipe on the sampled frames, baseline CNN (seed 0), threshold 0.7, vertical rescale to 16:9 for every picture that is not 16:9. Authors' predefined split, signer independence not verified. Validation videos only; no test video is used. Intervals are 95 percent Wilson; the paired test is the exact McNemar test (exact binomial test on the discordant videos).\n",
       "| Condition | Accuracy | 95% interval | Wrong accepted | Unrecognized | Top-1 | Frames with a hand |", "|---|---|---|---|---|---|---|"]
for k, v in C.items():
    n = len(v["rows"])
    a = sum(1 for r in v["rows"] if ok(r))
    lo, hi = wilson(a, n)
    out.append(f"| {k} | {a / n:.2f} | {lo:.2f} to {hi:.2f} | {v['wrong_accepted']:.2f} | {v['unrecognized']:.2f} | {v['top1']:.2f} | {v['hand_frame_rate']:.2f} |")
out += ["", "| Pair (first minus second) | first only right | second only right | exact McNemar p |", "|---|---|---|---|"]
pairs = [("native16x9", "small16x9"), ("native16x9", "lb4x3_black"), ("small16x9", "lb4x3_black"), ("lb4x3_edge", "lb4x3_black"), ("native16x9", "lb4x3_edge"),
         ("small16x9", "lb4x3_edge"), ("lb1x1_black", "lb4x3_black"), ("native16x9", "crop4x3"), ("lb4x3_edge", "crop4x3")]
for a, b in pairs:
    x, y, p = mcnemar(a, b)
    out.append(f"| {a} minus {b} | {x} | {y} | {p:.3f} |")
open(EV / "padding_test_val.md", "w", encoding="utf-8", newline="\n").write("\n".join(out) + "\n")
print("\n".join(out))
