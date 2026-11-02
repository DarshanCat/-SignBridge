"""Tables with intervals from the eval_matrix.py outputs. usage: python report_matrix.py <eval_val.json> [<eval_test.json>] <models_base> <models_aug>"""
import json
import math
import sys
from math import comb
from pathlib import Path

import numpy as np

args = sys.argv[1:]
val = json.load(open(args[0]))
test = json.load(open(args[1])) if len(args) == 4 else None
base_dir, aug_dir = Path(args[-2]), Path(args[-1])
ARCHS = ["cnn", "bigru", "transformer"]
KINDS = ["base", "aug"]
TH = [0.0, 0.3, 0.5, 0.7, 0.8, 0.9, 0.95]


def wilson(k, n, z=1.96):
    if n == 0:
        return (float("nan"),) * 2
    p = k / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return c - h, c + h


def counts(res, tau=0.7):
    c = w = u = 0
    for r in res:
        if r is None or r[1] < tau:
            u += 1
        elif r[0]:
            c += 1
        else:
            w += 1
    return c, w, u


def fmt(k, n):
    lo, hi = wilson(k, n)
    return f"{k / n:.2f} ({lo:.2f} to {hi:.2f})"


def mcnemar(a, b, tau=0.7):
    ok = lambda r: r is not None and r[1] >= tau and r[0]  # noqa: E731
    x = sum(1 for p, q in zip(a, b) if ok(p) and not ok(q))
    y = sum(1 for p, q in zip(a, b) if not ok(p) and ok(q))
    n = x + y
    if n == 0:
        return x, y, 1.0
    k = min(x, y)
    return x, y, min(1.0, 2 * sum(comb(n, i) for i in range(k + 1)) / 2**n)


def boot_diff(a, b, tau=0.7, reps=4000, seed=0):
    ok = lambda r: 1.0 if (r is not None and r[1] >= tau and r[0]) else 0.0  # noqa: E731
    d = np.array([ok(q) - ok(p) for p, q in zip(a, b)])
    rng = np.random.default_rng(seed)
    m = [d[rng.integers(0, len(d), len(d))].mean() for _ in range(reps)]
    return d.mean(), np.percentile(m, 2.5), np.percentile(m, 97.5)


def table_conditions(data, conds, title):
    print(f"\n### {title} (n = {data['n']} videos; accuracy at threshold 0.7 with 95 percent Wilson interval; wrong accepted; unrecognized)\n")
    print("| Condition | " + " | ".join(f"{k} {a}" for a in ARCHS for k in KINDS) + " |")
    print("|---|" + "---|" * (len(ARCHS) * 2))
    for c in conds:
        if c not in data["conditions"]:
            continue
        cells = []
        for a in ARCHS:
            for k in KINDS:
                res = data["conditions"][c][f"{k}_{a}"]
                cc, ww, uu = counts(res)
                n = len(res)
                cells.append(f"{fmt(cc, n)}; {ww / n:.2f}; {uu / n:.2f}")
        print(f"| {c} | " + " | ".join(cells) + " |")


def table_paired(data, conds, title):
    print(f"\n### {title}: augmented minus baseline, accuracy at 0.7 (paired bootstrap 95 percent interval; discordant videos base-only / aug-only; exact sign test p)\n")
    print("| Condition | " + " | ".join(ARCHS) + " |")
    print("|---|" + "---|" * len(ARCHS))
    for c in conds:
        if c not in data["conditions"]:
            continue
        cells = []
        for a in ARCHS:
            b, g = data["conditions"][c][f"base_{a}"], data["conditions"][c][f"aug_{a}"]
            d, lo, hi = boot_diff(b, g)
            x, y, p = mcnemar(b, g)
            cells.append(f"{d:+.2f} ({lo:+.2f} to {hi:+.2f}); {x}/{y}; p={p:.3f}")
        print(f"| {c} | " + " | ".join(cells) + " |")


def chosen_tau(model_dir):
    """Same rule as training.calibrate: lowest threshold with at least 95 percent accuracy on answered VALIDATION samples (offline val split)."""
    m = json.load(open(model_dir / "metrics.json"))
    for c in m["results"]["val"]["accuracy_vs_coverage"]:
        if c["threshold"] in TH and c["accuracy_on_answered"] is not None and c["accuracy_on_answered"] >= 0.95 and c["coverage"] > 0:
            return c["threshold"]
    return None


def table_tradeoff(data, cond):
    print(f"\n### Threshold trade-off, {cond}, {data['split']} corpus (n = {data['n']}): coverage and accuracy on answered, each with a 95 percent Wilson interval\n")
    print("| Model | " + " | ".join(f"tau {t:.2f}" for t in TH) + " |")
    print("|---|" + "---|" * len(TH))
    for a in ARCHS:
        for k in KINDS:
            res = data["conditions"][cond][f"{k}_{a}"]
            n = len(res)
            cells = []
            for t in TH:
                answered = [r for r in res if r is not None and r[1] >= t]
                right = sum(1 for r in answered if r[0])
                cov = len(answered) / n
                acc = f"{right / len(answered):.2f} ({wilson(right, len(answered))[0]:.2f} to {wilson(right, len(answered))[1]:.2f})" if answered else "n/a"
                cells.append(f"cov {cov:.2f}, acc {acc}")
            print(f"| {k} {a} | " + " | ".join(cells) + " |")


print("## Validation-chosen thresholds (offline validation split, rule of training.calibrate)")
for a in ARCHS:
    print(f"- {a}: baseline tau {chosen_tau(base_dir / a)}, augmented tau {chosen_tau(aug_dir / a)}")

table_conditions(val, ["offline", "br16x9", "br4x3", "br4x3_raw"], "Validation corpus, browser path")
table_conditions(val, [f"y_{k}" for k in (0.75, 0.9, 1.1, 1.25, 1.5)], "Validation corpus, y scale sweep on browser 16:9")
table_conditions(val, [f"noise_{s}" for s in (0.005, 0.01, 0.02)] + [f"drop_{r}" for r in (0.2, 0.4, 0.6)], "Validation corpus, noise and hand dropout sweeps on browser 16:9")
table_conditions(val, [f"zoom_{f}" for f in (1.0, 0.8, 0.6, 0.45)], "Validation corpus, framing (Python landmarks of shrunk frames)")
for f in (1.0, 0.8, 0.6, 0.45):
    w = val["conditions"].get(f"zoom_{f}_width")
    if w:
        print(f"zoom {f}: median shoulder width {np.median(w):.3f} (n={len(w)})")
table_paired(val, ["offline", "br16x9", "br4x3", "br4x3_raw", "y_0.9", "y_1.1", "y_1.25", "noise_0.01", "drop_0.2", "drop_0.4"], "Validation")
table_tradeoff(val, "br16x9")
table_tradeoff(val, "br4x3")
if test:
    table_conditions(test, ["offline", "br16x9", "br4x3", "br4x3_raw"], "TEST corpus, browser path (each final model evaluated once)")
    table_paired(test, ["offline", "br16x9", "br4x3", "br4x3_raw"], "Test")
    table_tradeoff(test, "br16x9")
    table_tradeoff(test, "br4x3")
