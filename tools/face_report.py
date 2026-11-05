"""Face block comparison: with face (data/models_face) against the three-seed baselines without face (seed 0 data/models_v2, seeds 1 and 2 data/models_seeds),
same data, split, settings and seeds. Everything is read from the models' metrics.json and, if present, the one-time test reports; nothing is typed in.
usage (repository root):  python -I tools/face_report.py
Writes docs/evaluation/face_results.md and face_results.json.
Statistics as in tools/browser_path/three_seed.py: difference seed by seed (face minus no face), mean, and a 95 percent t-interval over the three differences
(t = 4.303, 2 degrees of freedom); an interval that contains zero is reported as no clear change. Three seeds give wide intervals."""
import json
import math
import statistics as st
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EV = ROOT / "docs" / "evaluation"
ARCHS = ["cnn", "bigru", "transformer"]
BASE = {0: ROOT / "data" / "models_v2", 1: ROOT / "data" / "models_seeds" / "s1_base", 2: ROOT / "data" / "models_seeds" / "s2_base"}
FACE = {s: ROOT / "data" / "models_face" / f"s{s}" for s in (0, 1, 2)}
T95 = 4.303


def metrics(d):
    return json.loads((d / "metrics.json").read_text(encoding="utf-8"))


def val(d, key):
    return metrics(d)["results"]["val"][key]


def test_report(seed, arch):
    p = EV / "face" / f"test_s{seed}_{arch}.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else None


def delta(pairs):
    d = [f - b for b, f in pairs]
    m = st.mean(d)
    half = T95 * st.stdev(d) / math.sqrt(len(d))
    return {"per_seed": d, "mean": m, "lo": m - half, "hi": m + half, "clear": not (m - half <= 0 <= m + half)}


def fmt(x):
    return f"{x:.4f}"


rows, out = {}, []
for arch in ARCHS:
    for key in ("top1_accuracy", "macro_f1"):
        pairs = [(val(BASE[s] / arch, key), val(FACE[s] / arch, key)) for s in (0, 1, 2)]
        rows[f"{arch}.val.{key}"] = {"base": [b for b, _ in pairs], "face": [f for _, f in pairs], "delta": delta(pairs)}
    hp_b, hp_f = metrics(BASE[0] / arch)["hyperparameters"], metrics(FACE[0] / arch)["hyperparameters"]
    rows[f"{arch}.params"] = {"base": metrics(BASE[0] / arch)["parameters"], "face": metrics(FACE[0] / arch)["parameters"]}
    rows[f"{arch}.epochs"] = {"base": [metrics(BASE[s] / arch)["hyperparameters"]["epochs_run"] for s in (0, 1, 2)], "face": [metrics(FACE[s] / arch)["hyperparameters"]["epochs_run"] for s in (0, 1, 2)]}
    if test_report(0, arch):
        for key in ("top1_accuracy", "macro_f1"):
            base = [metrics(BASE[s] / arch)["results"]["test"][key] for s in (0, 1, 2)]
            face = [test_report(s, arch)[key] for s in (0, 1, 2)]
            rows[f"{arch}.test.{key}"] = {"base": base, "face": face, "delta": delta(list(zip(base, face)))}


def ms(xs):
    return f"{st.mean(xs):.4f} ± {st.stdev(xs):.4f}"


def dtext(d):
    return f"{d['mean']:+.4f} ({d['lo']:+.4f} to {d['hi']:+.4f})" + ("" if d["clear"] else ", no clear change")


P = out.append
P("# Face block: with and without eyebrows, eyes and mouth\n")
P("Authors' predefined split, signer independence not verified. INCLUDE v2 features (3121 train, 347 validation, 816 test samples). The face block is 50 MediaPipe Holistic "
  "face points (10 eyebrow, 12 eye, 28 mouth), normalized like the body (shoulder midpoint, shoulder width), appended to the 225 body features as a separate 150 value block (375 per frame). "
  "Same settings for both arms (epochs_max 60, patience 10, max_gap 3, batch 16, lr 0.001, seq_len 32, hidden 128, no augmentation), seeds 0, 1, 2. "
  "Mean ± sample SD over three independently trained models; difference taken seed by seed, 95 percent t-interval over the three differences. "
  "The without-face models are the three-seed baselines already reported in three_seed_results.md. No clip or sign is signer reviewed.\n")
P("## Validation (used for every decision)\n")
P("| Model | Metric | Without face | With face | Difference with face (95% interval) |")
P("|---|---|---|---|---|")
for arch in ARCHS:
    for key, name in (("macro_f1", "macro-F1"), ("top1_accuracy", "top-1")):
        r = rows[f"{arch}.val.{key}"]
        P(f"| {arch} | {name} | {ms(r['base'])} | {ms(r['face'])} | {dtext(r['delta'])} |")
P("\nPer seed (validation macro-F1, without face then with face):\n")
for arch in ARCHS:
    r = rows[f"{arch}.val.macro_f1"]
    P(f"- {arch}: seed 0 {fmt(r['base'][0])} to {fmt(r['face'][0])}, seed 1 {fmt(r['base'][1])} to {fmt(r['face'][1])}, seed 2 {fmt(r['base'][2])} to {fmt(r['face'][2])}")
P("\nParameters (seed 0): " + ", ".join(f"{a} {rows[f'{a}.params']['base']} to {rows[f'{a}.params']['face']}" for a in ARCHS) + ". Epochs run (seeds 0, 1, 2): " +
  "; ".join(f"{a} {rows[f'{a}.epochs']['base']} to {rows[f'{a}.epochs']['face']}" for a in ARCHS) + ".\n")
if rows.get("cnn.test.macro_f1"):
    P("## Test split (each face model evaluated once, after the validation comparison; the without-face numbers are the earlier one-time test evaluations)\n")
    P("| Model | Metric | Without face | With face | Difference with face (95% interval) |")
    P("|---|---|---|---|---|")
    for arch in ARCHS:
        for key, name in (("macro_f1", "macro-F1"), ("top1_accuracy", "top-1")):
            r = rows[f"{arch}.test.{key}"]
            P(f"| {arch} | {name} | {ms(r['base'])} | {ms(r['face'])} | {dtext(r['delta'])} |")
    P("")
(EV / "face_results.md").write_text("\n".join(out) + "\n", encoding="utf-8", newline="\n")
(EV / "face_results.json").write_text(json.dumps(rows, indent=1), encoding="utf-8", newline="\n")
print("\n".join(out))
