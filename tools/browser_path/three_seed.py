"""Three-seed aggregation of the browser-path evaluations (seed 0 from the first training run, seeds 1 and 2 from the twelve additional models).
Everything is computed from the per-video result files in docs/evaluation and the model metrics; nothing is typed in.
usage (repository root):  python -I tools/browser_path/three_seed.py
Writes docs/evaluation/three_seed_summary.json (cells of the report), three_seed_per_seed.json, three_seed_deltas.json and three_seed_results.md.

Statistics: mean and sample SD over the three independently trained models. For augmented minus baseline the difference is taken seed by seed
(seed 0 baseline against seed 0 augmented, and so on) and the interval is a 95 percent t-interval over the three differences (t = 4.303, 2 degrees
of freedom); an interval that contains zero is reported as "no clear change". Three seeds give wide intervals; this is a coarse check, not a test."""
import json
import math
import statistics as st
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EV = ROOT / "docs" / "evaluation"
ARCHS = ["cnn", "bigru", "transformer"]
KINDS = ["base", "aug"]
TH = [0.0, 0.3, 0.5, 0.7, 0.8, 0.9, 0.95]
CONDS = ["offline", "br16x9", "br4x3", "br4x3_raw"]
T95_DF2 = 4.303

DIRS = {
    0: (ROOT / "data" / "models_v2", ROOT / "data" / "models_aug_v1"),
    1: (ROOT / "data" / "models_seeds" / "s1_base", ROOT / "data" / "models_seeds" / "s1_aug"),
    2: (ROOT / "data" / "models_seeds" / "s2_base", ROOT / "data" / "models_seeds" / "s2_aug"),
}
SUF = {0: "", 1: "_s1", 2: "_s2"}
VAL = {s: EV / f"eval_val{SUF[s]}.json" for s in SUF}
TEST = {s: EV / f"eval_test{SUF[s]}.json" for s in SUF}


def chosen_tau(model_dir):
    """Rule of training.calibrate: lowest threshold with at least 95 percent accuracy on answered VALIDATION samples (offline validation split)."""
    m = json.load(open(model_dir / "metrics.json"))
    for c in m["results"]["val"]["accuracy_vs_coverage"]:
        if c["threshold"] in TH and c["accuracy_on_answered"] is not None and c["accuracy_on_answered"] >= 0.95 and c["coverage"] > 0:
            return c["threshold"]
    return None


def counts(res, tau):
    c = w = u = 0
    for r in res:
        if r is None or r[1] < tau:
            u += 1
        elif r[0]:
            c += 1
        else:
            w += 1
    n = len(res)
    return c / n, w / n, u / n


def top1(res):
    return sum(1 for r in res if r is not None and r[0]) / len(res)


def ms(xs):
    return st.mean(xs), (st.stdev(xs) if len(xs) > 1 else 0.0)


def cell(xs):
    m, s = ms(xs)
    return f"{m:.2f} ± {s:.2f}"


def delta(xs_base, xs_aug):
    d = [b - a for a, b in zip(xs_base, xs_aug)]
    m, s = ms(d)
    half = T95_DF2 * s / math.sqrt(len(d))
    lo, hi = m - half, m + half
    return {"per_seed": d, "mean": m, "lo": lo, "hi": hi, "clear": not (lo <= 0 <= hi)}


def dtext(dd):
    return f"{dd['mean']:+.2f} ({dd['lo']:+.2f} to {dd['hi']:+.2f})" + ("" if dd["clear"] else " no clear change")


per, taus, nofall = {}, {}, []
for seed in (0, 1, 2):
    val, test = json.load(open(VAL[seed])), json.load(open(TEST[seed]))
    for kind, d in zip(KINDS, DIRS[seed]):
        for a in ARCHS:
            name = f"{a}_{kind}"
            tau = chosen_tau(d / a)
            if tau is None:
                nofall.append((name, seed))
                tau = 0.95
            taus.setdefault(name, []).append(tau)
            for split, data in (("val", val), ("test", test)):
                for c in CONDS:
                    res = data["conditions"][c][f"{kind}_{a}"]
                    acc, wa, un = counts(res, tau)
                    slot = per.setdefault(name, {}).setdefault(f"{split}.{c}", {})
                    for k, v in (("acc", acc), ("wa", wa), ("unrec", un), ("top1", top1(res))):
                        slot.setdefault(k, []).append(v)

summary = {}
for name in per:
    for c in CONDS:
        summary[f"{name}.{c}"] = cell(per[name][f"test.{c}"]["acc"])
    summary[f"{name}.wrong_accepted"] = cell(per[name]["test.br16x9"]["wa"])
    summary[f"{name}.threshold"] = ", ".join(f"{t:g}" for t in taus[name])

deltas = {}
for a in ARCHS:
    for c in CONDS:
        deltas[f"{a}.{c}.acc"] = delta(per[f"{a}_base"][f"test.{c}"]["acc"], per[f"{a}_aug"][f"test.{c}"]["acc"])
        deltas[f"{a}.{c}.top1"] = delta(per[f"{a}_base"][f"test.{c}"]["top1"], per[f"{a}_aug"][f"test.{c}"]["top1"])
    deltas[f"{a}.br16x9.wa"] = delta(per[f"{a}_base"]["test.br16x9"]["wa"], per[f"{a}_aug"]["test.br16x9"]["wa"])
    deltas[f"{a}.gap"] = {k: [x - y for x, y in zip(per[f"{a}_{k}"]["test.br16x9"]["acc"], per[f"{a}_{k}"]["test.br4x3"]["acc"])] for k in KINDS}
    deltas[f"{a}.gapchange"] = delta(deltas[f"{a}.gap"]["base"], deltas[f"{a}.gap"]["aug"])
    summary[f"delta.{a}.gapchange"] = dtext(deltas[f"{a}.gapchange"])
for k, dd in deltas.items():
    if "per_seed" in dd:
        summary[f"delta.{k}"] = dtext(dd)

# seed-0 validation sweeps (the sweeps were not run for seeds 1 and 2)
val0 = json.load(open(VAL[0]))
sweep = {}
for a in ARCHS:
    for c in ("y_0.9", "y_1.25", "noise_0.01", "drop_0.2"):
        row = {}
        for kind in KINDS:
            tau = taus[f"{a}_{kind}"][0]
            row[kind] = counts(val0["conditions"][c][f"{kind}_{a}"], tau)[0]
        sweep[f"{a}.{c}"] = row
        summary[f"sweep.{a}.{c}"] = f"{row['base']:.2f} to {row['aug']:.2f}"

# threshold trade-off cells: seed 0, baseline CNN in the browser path (test corpus) and augmented CNN offline on the full test split
test0 = json.load(open(TEST[0]))
res = test0["conditions"]["br16x9"]["base_cnn"]
tradeoff = {}
aug_m = json.load(open(DIRS[0][1] / "cnn" / "metrics.json"))["results"]["test"]["accuracy_vs_coverage"]
for t in TH:
    ans = [r for r in res if r is not None and r[1] >= t]
    right = sum(1 for r in ans if r[0])
    row = {"browser_cov": len(ans) / len(res), "browser_acc": right / len(ans) if ans else None}
    m = next(c for c in aug_m if c["threshold"] == t)
    row.update({"aug_offline_cov": m["coverage"], "aug_offline_acc": m["accuracy_on_answered"]})
    tradeoff[f"{t:g}"] = row

json.dump({"taus": taus, "per_seed": per, "tau_fallback_used_for": nofall}, open(EV / "three_seed_per_seed.json", "w"), indent=1)
json.dump({"deltas": deltas, "seed0_val_sweeps": sweep, "tradeoff_seed0": tradeoff}, open(EV / "three_seed_deltas.json", "w"), indent=1)
json.dump(summary, open(EV / "three_seed_summary.json", "w"), indent=1)

out = []
P = out.append
P("# Three-seed results\n")
P("Authors' predefined split, signer independence not verified. Seed 0 is the earlier training run; seeds 1 and 2 are the twelve additional models. Mean ± sample SD over three independently trained models. Each model has its own validation-chosen threshold (lowest threshold with at least 95 percent accuracy on answered validation samples, offline). Browser conditions use the browser-path TEST corpus (312 videos, one evaluation per trained model); the offline column is the stored features of the same 312 videos, not the full 816-sample test split. Three seeds are few: the SD is a rough indication, not an interval.\n")
for split, title in (("test", "Test corpus (312 videos), accuracy at the validation-chosen threshold"), ("val", "Validation corpus (211 videos), accuracy at the validation-chosen threshold")):
    P(f"## {title}\n")
    P("| Condition | " + " | ".join(f"{k} {a}" for a in ARCHS for k in KINDS) + " |")
    P("|---|" + "---|" * 6)
    for c in CONDS:
        P(f"| {c} | " + " | ".join(cell(per[f'{a}_{k}'][f'{split}.{c}']['acc']) for a in ARCHS for k in KINDS) + " |")
    for lab, c in (("wrong accepted, br16x9", "br16x9"), ("wrong accepted, br4x3", "br4x3"), ("wrong accepted, br4x3_raw", "br4x3_raw")):
        P(f"| {lab} | " + " | ".join(cell(per[f'{a}_{k}'][f'{split}.{c}']['wa']) for a in ARCHS for k in KINDS) + " |")
    P("")
P("## Per-model validation-chosen thresholds (seed 0, 1, 2)\n")
for name in per:
    P(f"- {name}: {', '.join(f'{t:g}' for t in taus[name])}")
if nofall:
    P(f"\nNo threshold reached 95 percent accuracy on answered validation samples for: {nofall}; 0.95 was used for them.")
P("\n## Gap and augmentation effect (test corpus)\n")
P("16:9 minus rescaled 4:3 accuracy, per seed:\n")
P("| Model | 16:9 minus 4:3 (mean) | per-seed |")
P("|---|---|---|")
for a in ARCHS:
    for k in KINDS:
        g = deltas[f"{a}.gap"][k]
        P(f"| {a}_{k} | {st.mean(g):+.2f} | {', '.join(f'{x:+.2f}' for x in g)} |")
P("")
for a in ARCHS:
    P(f"Change of the 16:9 minus 4:3 gap (augmented minus baseline), {a}: {dtext(deltas[f'{a}.gapchange'])}  ")
P("\nAugmented minus baseline, taken seed by seed; interval = 95 percent t-interval over the three differences (an interval that contains zero is written \"no clear change\").\n")
P("| Architecture | Condition | accuracy at threshold | top-1 (no threshold) | per-seed accuracy differences |")
P("|---|---|---|---|---|")
for a in ARCHS:
    for c in CONDS:
        P(f"| {a} | {c} | {dtext(deltas[f'{a}.{c}.acc'])} | {dtext(deltas[f'{a}.{c}.top1'])} | {', '.join(f'{x:+.2f}' for x in deltas[f'{a}.{c}.acc']['per_seed'])} |")
    P(f"| {a} | wrong accepted, br16x9 | {dtext(deltas[f'{a}.br16x9.wa'])} | | {', '.join(f'{x:+.2f}' for x in deltas[f'{a}.br16x9.wa']['per_seed'])} |")
P("\n## Seed 0 only: validation sweeps, accuracy baseline to augmented (not run for seeds 1 and 2)\n")
P("| Architecture | y scale 0.9 | y scale 1.25 | noise 0.01 | dropout 0.2 |")
P("|---|---|---|---|---|")
for a in ARCHS:
    P(f"| {a} | " + " | ".join(summary[f"sweep.{a}.{c}"] for c in ("y_0.9", "y_1.25", "noise_0.01", "drop_0.2")) + " |")
P("\n## Seed 0 only: threshold trade-off (coverage / accuracy on answered)\n")
P("| Threshold | baseline CNN, browser 16:9, 312 test videos | augmented CNN, offline, 816 test samples |")
P("|---|---|---|")
for t, r in tradeoff.items():
    P(f"| {t} | {r['browser_cov']:.4f} / {r['browser_acc']:.4f} | {r['aug_offline_cov']:.4f} / {r['aug_offline_acc']:.4f} |")
open(EV / "three_seed_results.md", "w", encoding="utf-8", newline="\n").write("\n".join(out) + "\n")
print("\n".join(out))
